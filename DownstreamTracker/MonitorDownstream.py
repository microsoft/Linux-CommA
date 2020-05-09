import logging
import sys
from pathlib import Path

from git import Repo

import Util.Config
import Util.Constants as cst
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.SqlClasses import (
    Distros,
    MonitoringSubjects,
    MonitoringSubjectsMissingPatches,
    PatchData,
)
from DownstreamTracker.DownstreamMatcher import DownstreamMatcher
from UpstreamTracker.MonitorUpstream import get_hyperv_filenames
from UpstreamTracker.ParseData import process_commits

# from DownstreamTracker.DebianParser import monitor_debian


def update_revisions_for_distro(distro_id, revs):
    """
    Updates the database with the given revisions

    new_revisions: list of <revision>s to add under this distro_id
    """
    with DatabaseDriver.get_session() as s:
        revs_to_delete = (
            s.query(MonitoringSubjects)
            .filter_by(distroID=distro_id)
            .filter(~MonitoringSubjects.revision.in_(revs))
        )
        for r in revs_to_delete:
            logging.info(f"For distro {distro_id}, deleting revision: {r.revision}")

        # This is a bulk delete and we close the session immediately after.
        revs_to_delete.delete(synchronize_session=False)

    with DatabaseDriver.get_session() as s:
        for rev in revs:
            # Only add if it doesn't already exist. We're dealing
            # with revisions on the scale of 1, so the number of
            # queries and inserts here doesn't matter.
            if (
                s.query(MonitoringSubjects)
                .filter_by(distroID=distro_id, revision=rev)
                .first()
                is None
            ):
                logging.info(f"For distro {distro_id}, adding revision: {rev}")
                s.add(MonitoringSubjects(distroID=distro_id, revision=rev))


def update_tracked_revisions(distro_id, repo):
    """
    This updates the stored two latest revisions stored per distro_id.
    This method contains distro-specific logic

    repo: the git repo object of whatever repo to check revisions in
    """

    # TODO This is WRONG it's sorting by alphabetization,
    # which happens to be correct currently but needs to be addressed
    # git tag can sort by date, but can't specify remote. ls-remote can't naturally sort
    # until git 1.2.18 - 1.2.17 is the latest version Ubuntu18.04 can get

    if distro_id.startswith("Ubuntu"):
        latest_two_kernels = []
        tag_lines = repo.git.ls_remote("--t", "--refs", distro_id).split("\n")
        tag_names = [tag_line.rpartition("/")[-1] for tag_line in tag_lines]
        # Filter out edge, and only include azure revisions
        tag_names = list(filter(lambda x: "azure" in x and "edge" not in x, tag_names))
        latest_two_kernels = tag_names[-2:]
        update_revisions_for_distro(distro_id, latest_two_kernels)


# TODO: Refactor this function into a smaller set of pieces.
def monitor_subject(monitoring_subject, repo):
    """
    Update the missing patches in the database for this monitoring_subject

    monitoring_subject: The MonitoringSubject we are updating
    repo: The git repo object pointing to relevant upstream linux repo
    """

    missing_patch_ids = None
    paths = get_hyperv_filenames(repo)

    # This returns patches missing in the repo with very good accuracy, but isn't perfect
    # So, we run extra checks to confirm the missing patches.
    missing_commit_ids = repo.git.log(
        "--no-merges",
        "--right-only",
        "--cherry-pick",
        "--pretty=format:%H",
        "%s...master" % monitoring_subject.revision,
        "--",
        paths,
    ).split("\n")
    logging.debug("Retrived missing patches through cherry-pick")

    # Run extra checks on these missing commits
    with DatabaseDriver.get_session() as s:
        upstream_missing_patches = (
            s.query(PatchData).filter(PatchData.commitID.in_(missing_commit_ids)).all()
        )
        num_log_missing_patches = len(upstream_missing_patches)
        # We only want to check downstream patches as old as the
        # oldest upstream missing patch's commit_time, as an
        # optimization.
        earliest_commit_date = min(
            p.commitTime for p in upstream_missing_patches
        ).isoformat()
        logging.debug(f"Processing commits since {earliest_commit_date}")
        downstream_patches = process_commits(
            repo, monitoring_subject.revision, paths, since=earliest_commit_date,
        )
        downstream_matcher = DownstreamMatcher(downstream_patches)

        logging.info(
            f"Starting confidence matching for {len(upstream_missing_patches)} upstream patches "
        )
        # Removes patches which our algorithm say exist downstream.
        missing_patches = [
            p
            for p in upstream_missing_patches
            if not downstream_matcher.exists_matching_patch(p)
        ]

        logging.info(
            "Number of patches missing from git log to our algo: "
            + f"{num_log_missing_patches} -> {len(missing_patches)}."
        )

        missing_patch_ids = [p.patchID for p in missing_patches]

    subject_id = monitoring_subject.monitoringSubjectID

    # Delete patches that are no longer missing.
    #
    # NOTE: We do this in separate sessions in order to cleanly expire
    # their objects and commit the changes to the database. There is
    # surely another way to do this, but it works.
    with DatabaseDriver.get_session() as s:
        patches = s.query(MonitoringSubjectsMissingPatches).filter_by(
            monitoringSubjectID=subject_id
        )
        # Delete patches that are no longer missing: the patchID is
        # NOT IN the latest set of missing patchIDs.
        patches_to_delete = patches.filter(
            ~MonitoringSubjectsMissingPatches.patchID.in_(missing_patch_ids)
        )
        logging.info(
            f"Deleting {patches_to_delete.count()} patches that are now present."
        )
        # This is a bulk delete and we close the session immediately after.
        patches_to_delete.delete(synchronize_session=False)

    # Add patches which are newly missing.
    with DatabaseDriver.get_session() as s:
        patches = s.query(MonitoringSubjectsMissingPatches).filter_by(
            monitoringSubjectID=subject_id
        )
        new_missing_patches = 0
        for patch_id in missing_patch_ids:
            # Only add if it doesn't already exist. We're dealing with
            # patches on the scale of 100, so the number of queries
            # and inserts here doesn't matter.
            if patches.filter_by(patchID=patch_id).first() is None:
                new_missing_patches += 1
                s.add(
                    MonitoringSubjectsMissingPatches(
                        monitoringSubjectID=subject_id, patchID=patch_id
                    )
                )
        logging.info(f"Adding {new_missing_patches} patches that are now missing.")


def monitor_downstream():
    print("Monitoring downstream...")
    # Linux repo is assumed to be present
    repo_path = Path(cst.PATH_TO_REPOS, cst.LINUX_REPO_NAME).resolve()
    if not repo_path.exists():
        logging.error("Linux repo does not exist! Run with `--upstream` first!")
        sys.exit(1)
    repo = Repo(repo_path)

    # Add repos as a remote origin if not already added
    current_remotes = repo.git.remote()
    with DatabaseDriver.get_session() as s:
        for distroID, repoLink in s.query(Distros.distroID, Distros.repoLink).all():
            # Debian we handle differently
            if distroID not in current_remotes and not distroID.startswith("Debian"):
                logging.debug(
                    "Adding remote origin for %s from %s" % (distroID, repoLink)
                )
                repo.create_remote(distroID, url=repoLink)

    # Update all remotes, and tags of all remotes
    if Util.Config.fetch:
        logging.info("Fetching updates to all repos and tags.")
        repo.git.fetch(
            f"--all", "--tags", "--force", "--shallow-since='{Util.Config.since}'"
        )
        logging.debug("Fetched!")

    logging.info("Updating tracked revisions for each repo.")
    # Update stored revisions for repos as appropriate
    with DatabaseDriver.get_session() as s:
        for (distroID,) in s.query(Distros.distroID).all():
            update_tracked_revisions(distroID, repo)

    with DatabaseDriver.get_session() as s:
        for subject in s.query(MonitoringSubjects).all():
            if subject.distroID.startswith("Debian"):
                # TODO don't skip debian
                logging.debug("skipping debian")
            else:
                logging.info(
                    "Monitoring Script starting for Distro: %s, revision: %s"
                    % (subject.distroID, subject.revision)
                )
                monitor_subject(subject, repo)
    print("Finished monitoring downstream!")
