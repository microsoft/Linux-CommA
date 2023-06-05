# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions for monitoring downstream repos for missing commits
"""

import logging

import approxidate
import git

from comma.database.driver import DatabaseDriver
from comma.database.model import (
    Distros,
    MonitoringSubjects,
    MonitoringSubjectsMissingPatches,
    PatchData,
)
from comma.downstream.matcher import patch_matches
from comma.upstream import process_commits
from comma.util import config
from comma.util.tracking import GitProgressPrinter, get_linux_repo, get_tracked_paths


def update_revisions_for_distro(distro_id, revs):
    """
    Updates the database with the given revisions

    new_revisions: list of <revision>s to add under this distro_id
    """
    with DatabaseDriver.get_session() as session:
        revs_to_delete = (
            session.query(MonitoringSubjects)
            .filter_by(distroID=distro_id)
            .filter(~MonitoringSubjects.revision.in_(revs))
        )
        for subject in revs_to_delete:
            logging.info("For distro %s, deleting revision: %s", distro_id, subject.revision)

        # This is a bulk delete and we close the session immediately after.
        revs_to_delete.delete(synchronize_session=False)

    with DatabaseDriver.get_session() as session:
        for rev in revs:
            # Only add if it doesn't already exist. We're dealing
            # with revisions on the scale of 1, so the number of
            # queries and inserts here doesn't matter.
            if (
                session.query(MonitoringSubjects)
                .filter_by(distroID=distro_id, revision=rev)
                .first()
                is None
            ):
                logging.info("For distro %s, adding revision: %s", distro_id, rev)
                session.add(MonitoringSubjects(distroID=distro_id, revision=rev))


def update_tracked_revisions(distro_id, repo):
    """
    This updates the stored two latest revisions stored per distro_id.
    This method contains distro-specific logic

    repo: the git repo object of whatever repo to check revisions in
    """
    # This sorts alphabetically and not by the actual date
    # While technically wrong, this is preferred
    # ls-remote could naturally sort by date, but that would require all the objects to be local

    if distro_id.startswith("Ubuntu"):
        tag_names = []
        for line in repo.git.ls_remote(
            "--tags", "--refs", "--sort=v:refname", distro_id
        ).splitlines():
            name = line.split("/", 1)[-1]
            if "azure" in name and all(label not in name for label in ("edge", "cvm", "fde")):
                tag_names.append(name)

        update_revisions_for_distro(distro_id, tag_names[-2:])


def get_missing_cherries(repo, reference):
    """
    Get a list of cherry-picked commits missing from the downstream reference
    """

    # Get all upstream commits on tracked paths within window
    upstream_commits = set(
        repo.git.log(
            "--no-merges",
            "--pretty=format:%H",
            f"--since={config.since}",
            "origin/master",
            "--",
            get_tracked_paths(),
        ).splitlines()
    )

    # Get missing cherries for all paths, but don't filter by path since it takes forever
    missing_cherries = set(
        repo.git.log(
            "--no-merges",
            "--right-only",
            "--cherry-pick",
            "--pretty=format:%H",
            f"--since={config.since}",
            f"{reference}...origin/master",
        ).splitlines()
    )

    return missing_cherries & upstream_commits


def monitor_subject(monitoring_subject, repo, reference=None):
    """
    Update the missing patches in the database for this monitoring_subject

    monitoring_subject: The MonitoringSubject we are updating
    repo: The git repo object pointing to relevant upstream Linux repo
    """

    reference = monitoring_subject.revision if reference is None else reference

    missing_cherries = get_missing_cherries(repo, reference)
    logging.debug("Found %d missing patches through cherry-pick.", len(missing_cherries))

    # Run extra checks on these missing commits
    missing_patch_ids = get_missing_patch_ids(missing_cherries, reference)
    logging.info("Identified %d missing patches", len(missing_patch_ids))

    # Delete patches that are no longer missing.
    # NOTE: We do this in separate sessions in order to cleanly expire their objects and commit the
    # changes to the database. There is surely another way to do this, but it works.
    subject_id = monitoring_subject.monitoringSubjectID
    with DatabaseDriver.get_session() as session:
        patches = session.query(MonitoringSubjectsMissingPatches).filter_by(
            monitoringSubjectID=subject_id
        )
        # Delete patches that are no longer missing: the patchID is
        # NOT IN the latest set of missing patchIDs.
        patches_to_delete = patches.filter(
            ~MonitoringSubjectsMissingPatches.patchID.in_(missing_patch_ids)
        )
        logging.info("Deleting %d patches that are now present.", patches_to_delete.count())
        # This is a bulk delete and we close the session immediately after.
        patches_to_delete.delete(synchronize_session=False)

    # Add patches which are newly missing.
    with DatabaseDriver.get_session() as session:
        patches = session.query(MonitoringSubjectsMissingPatches).filter_by(
            monitoringSubjectID=subject_id
        )
        new_missing_patches = 0
        for patch_id in missing_patch_ids:
            # Only add if it doesn't already exist. We're dealing with patches on the scale of 100,
            # so the number of queries and inserts here doesn't matter.
            if patches.filter_by(patchID=patch_id).first() is None:
                new_missing_patches += 1
                session.add(
                    MonitoringSubjectsMissingPatches(
                        monitoringSubjectID=subject_id, patchID=patch_id
                    )
                )
        logging.info("Adding %d patches that are now missing.", new_missing_patches)


def get_missing_patch_ids(missing_cherries, reference):
    """
    Attempt to determine which patches are missing from a list of missing cherries
    """

    with DatabaseDriver.get_session() as session:
        patches = (
            session.query(PatchData)
            .filter(PatchData.commitID.in_(missing_cherries))
            .order_by(PatchData.commitTime)
            .all()
        )
        # We only want to check downstream patches as old as the oldest upstream missing patch
        earliest_commit_date = min(patch.commitTime for patch in patches).isoformat()
        logging.debug("Processing commits since %s", earliest_commit_date)

        # Get the downstream commits for this revision (these are distinct from upstream because
        # they have been cherry-picked). This is slow but necessary!
        downstream_patches = process_commits(revision=reference, since=earliest_commit_date)

        # Double check the missing cherries using our fuzzy algorithm.
        logging.info("Starting confidence matching for %d upstream patches...", len(patches))
        missing_patches = [p.patchID for p in patches if not patch_matches(downstream_patches, p)]

    return missing_patches


def fetch_remote_ref(repo: git.Repo, name: str, local_ref: str, remote_ref: str) -> None:
    """
    Shallow fetch remote reference so it is available locally
    """

    remote = repo.remote(name)

    # Initially fetch revision at depth 1
    logging.info("Fetching remote ref %s from remote %s at depth 1", remote_ref, remote)
    fetch_info = remote.fetch(remote_ref, depth=1, verbose=True, progress=GitProgressPrinter())

    # If last commit for revision is in the fetch window, expand depth
    # This check is necessary because some servers will throw an error when there are
    # no commits in the fetch window
    if fetch_info[-1].commit.committed_date >= approxidate.approx(config.since):
        logging.info(
            'Fetching ref %s from remote %s shallow since "%s"',
            remote_ref,
            remote,
            config.since,
        )
        try:
            remote.fetch(
                remote_ref,
                shallow_since=config.since,
                verbose=True,
                progress=GitProgressPrinter(),
            )
        except git.GitCommandError as e:
            # ADO repos do not currently support --shallow-since, only depth
            if "Server does not support --shallow-since" in e.stderr:
                logging.warning(
                    "Server does not support --shallow-since, retrying fetch without option."
                )
                remote.fetch(remote_ref, verbose=True, progress=GitProgressPrinter())
            else:
                raise
    else:
        logging.info(
            'Newest commit for ref %s from remote %s is older than fetch window "%s"',
            remote_ref,
            remote,
            config.since,
        )

    # Create tag at FETCH_HEAD to preserve reference locally
    if not hasattr(repo.references, local_ref):
        repo.create_tag(local_ref, "FETCH_HEAD")


def monitor_downstream():
    """
    Cycle through downstream remotes and search for missing commits
    """

    print("Monitoring downstream...")
    repo = get_linux_repo()

    # Add repos as a remote if not already added
    with DatabaseDriver.get_session() as session:
        for distro_id, url in session.query(Distros.distroID, Distros.repoLink).all():
            # Skip Debian for now
            if distro_id not in repo.remotes and not distro_id.startswith("Debian"):
                logging.debug("Adding remote %s from %s", distro_id, url)
                repo.create_remote(distro_id, url=url)

    # Update stored revisions for repos as appropriate
    logging.info("Updating tracked revisions for each repo.")
    with DatabaseDriver.get_session() as session:
        for (distro_id,) in session.query(Distros.distroID).all():
            update_tracked_revisions(distro_id, repo)

    with DatabaseDriver.get_session() as session:
        for subject in session.query(MonitoringSubjects).all():
            if subject.distroID.startswith("Debian"):
                # TODO (Issue 51): Don't skip Debian
                logging.debug("skipping Debian")
                continue

            # Use distro name for local refs to prevent duplicates
            if subject.revision.startswith(f"{subject.distroID}/"):
                local_ref = subject.revision
                remote_ref = subject.revision.split("/", 1)[-1]
            else:
                local_ref = f"{subject.distroID}/{subject.revision}"
                remote_ref = subject.revision

            fetch_remote_ref(repo, subject.distroID, local_ref, remote_ref)

            logging.info(
                "Monitoring Script starting for Distro: %s, revision: %s",
                subject.distroID,
                remote_ref,
            )
            monitor_subject(subject, repo, local_ref)

    print("Finished monitoring downstream!")
