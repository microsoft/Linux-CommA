import os

import git

import Util.Constants as cst
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.MissingPatchesDatabaseDriver import MissingPatchesDatabaseDriver
from DatabaseDriver.MonitoringSubjectDatabaseDriver import (
    MonitoringSubjectDatabaseDriver,
)
from DatabaseDriver.SqlClasses import Distros, MonitoringSubjects, PatchData
from DownstreamTracker.DownstreamMatcher import DownstreamMatcher
from UpstreamTracker.MonitorUpstream import get_hyperv_filenames
from UpstreamTracker.ParseData import process_commits

# from DownstreamTracker.DebianParser import monitor_debian


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
        db_driver = MonitoringSubjectDatabaseDriver()
        db_driver.update_revisions_for_distro(distro_id, latest_two_kernels)


def monitor_subject(monitoring_subject, repo):
    """
    Update the missing patches in the database for this monitoring_subject

    monitoring_subject: The MonitoringSubject we are updating
    repo: The git repo object pointing to relevant upstream linux repo
    """

    filenames = get_hyperv_filenames(repo)

    # This returns patches missing in the repo with very good accuracy, but isn't perfect
    # So, we run extra checks to confirm the missing patches.
    missing_commit_ids = repo.git.log(
        "--no-merges",
        "--right-only",
        "--cherry-pick",
        "--pretty=format:%H",
        "%s...master" % monitoring_subject.revision,
        "--",
        filenames,
    ).split("\n")

    # Run extra checks on these missing commits
    with DatabaseDriver.get_session() as s:
        missing_patches = (
            s.query(PatchData).filter(PatchData.commitID.in_(missing_commit_ids)).all()
        )
        num_log_missing_patches = len(missing_patches)
        # We only want to check downstream patches as old as the
        # oldest missing patch's commit_time, as an optimization.
        earliest_commit_date = min(p.commitTime for p in missing_patches)
        downstream_patches = process_commits(
            repo,
            monitoring_subject.revision,
            filenames,
            since_time=earliest_commit_date,
        )
        downstream_matcher = DownstreamMatcher(downstream_patches)
        # Removes patches which our algorithm say exist downstream
        missing_patches = list(
            filter(
                lambda p: not downstream_matcher.exists_matching_patch(p),
                missing_patches,
            )
        )
        print(
            "[Info] Number of patches missing from git log to our algo: %s -> %s."
            % (num_log_missing_patches, len(missing_patches))
        )

        missing_patch_ids = [p.patchID for p in missing_patches]
        # Update database to reflect latest missing patches
        missing_patches_db_driver = MissingPatchesDatabaseDriver()
        missing_patches_db_driver.update_missing_patches(
            monitoring_subject.monitoringSubjectID, missing_patch_ids
        )


def monitor_downstream():
    # Linux repo is assumed to be present
    path_to_linux = os.path.join(cst.PATH_TO_REPOS, cst.LINUX_REPO_NAME)
    repo = git.Repo(path_to_linux)

    # Add repos as a remote origin if not already added
    current_remotes = repo.git.remote()
    with DatabaseDriver.get_session() as s:
        for distroID, repoLink in s.query(Distros.distroID, Distros.repoLink).all():
            # Debian we handle differently
            if distroID not in current_remotes and not distroID.startswith("Debian"):
                print(
                    "[Info] Adding remote origin for %s from %s" % (distroID, repoLink)
                )
                repo.create_remote(distroID, url=repoLink)

    # Update all remotes, and tags of all remotes
    print("[Info] Fetching updates to all repos and tags.")
    repo.git.fetch("--all")
    repo.git.fetch("--all", "--tags")

    print("[Info] Updating tracked revisions for each repo.")
    # Update stored revisions for repos as appropriate
    with DatabaseDriver.get_session() as s:
        for (distroID,) in s.query(Distros.distroID).all():
            update_tracked_revisions(distroID, repo)

    with DatabaseDriver.get_session() as s:
        for subject in s.query(MonitoringSubjects).all():
            if subject.distroID.startswith("Debian"):
                # TODO don't skip debian
                print("skipping debian")
            else:
                print(
                    "[Info] Monitoring Script starting for Distro: %s, revision: %s.."
                    % (subject.distroID, subject.revision)
                )
                monitor_subject(subject, repo)

    print("Patch Tracker finished.")
