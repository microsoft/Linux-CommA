# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions for monitoring downstream repos for missing commits
"""

import logging

from comma.database.driver import DatabaseDriver
from comma.database.model import (
    Distros,
    MonitoringSubjects,
    MonitoringSubjectsMissingPatches,
    PatchData,
)
from comma.downstream.matcher import patch_matches
from comma.upstream import process_commits
from comma.util.tracking import get_linux_repo


LOGGER = logging.getLogger(__name__)


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
            LOGGER.info("For distro %s, deleting revision: %s", distro_id, subject.revision)

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
                LOGGER.info("For distro %s, adding revision: %s", distro_id, rev)
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
        tag_names = tuple(
            tag
            for tag in repo.get_remote_tags(distro_id)
            if "azure" in tag and all(label not in tag for label in ("edge", "cvm", "fde"))
        )
        update_revisions_for_distro(distro_id, tag_names[-2:])


def monitor_subject(monitoring_subject, repo, reference=None):
    """
    Update the missing patches in the database for this monitoring_subject

    monitoring_subject: The MonitoringSubject we are updating
    repo: The git repo object pointing to relevant upstream Linux repo
    """

    reference = monitoring_subject.revision if reference is None else reference

    missing_cherries = repo.get_missing_cherries(reference, repo.get_tracked_paths())
    LOGGER.debug("Found %d missing patches through cherry-pick.", len(missing_cherries))

    # Run extra checks on these missing commits
    missing_patch_ids = get_missing_patch_ids(missing_cherries, reference)
    LOGGER.info("Identified %d missing patches", len(missing_patch_ids))

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
        LOGGER.info("Deleting %d patches that are now present.", patches_to_delete.count())
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
        LOGGER.info("Adding %d patches that are now missing.", new_missing_patches)


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
        LOGGER.debug("Processing commits since %s", earliest_commit_date)

        # Get the downstream commits for this revision (these are distinct from upstream because
        # they have been cherry-picked). This is slow but necessary!
        downstream_patches = process_commits(revision=reference, since=earliest_commit_date)

        # Double check the missing cherries using our fuzzy algorithm.
        LOGGER.info("Starting confidence matching for %d upstream patches...", len(patches))
        missing_patches = [p.patchID for p in patches if not patch_matches(downstream_patches, p)]

    return missing_patches


def monitor_downstream():
    """
    Cycle through downstream remotes and search for missing commits
    """

    repo = get_linux_repo()

    # Add repos as a remote if not already added
    with DatabaseDriver.get_session() as session:
        for distro_id, url in session.query(Distros.distroID, Distros.repoLink).all():
            # Skip Debian for now
            if distro_id not in repo.remotes and not distro_id.startswith("Debian"):
                LOGGER.debug("Adding remote %s from %s", distro_id, url)
                repo.create_remote(distro_id, url=url)

    # Update stored revisions for repos as appropriate
    LOGGER.info("Updating tracked revisions for each repo.")
    with DatabaseDriver.get_session() as session:
        for (distro_id,) in session.query(Distros.distroID).all():
            update_tracked_revisions(distro_id, repo)

    with DatabaseDriver.get_session() as session:
        subjects = session.query(MonitoringSubjects).all()
        total = len(subjects)

        for num, subject in enumerate(subjects, 1):
            if subject.distroID.startswith("Debian"):
                # TODO (Issue 51): Don't skip Debian
                LOGGER.debug("skipping Debian")
                continue

            # Use distro name for local refs to prevent duplicates
            if subject.revision.startswith(f"{subject.distroID}/"):
                local_ref = subject.revision
                remote_ref = subject.revision.split("/", 1)[-1]
            else:
                local_ref = f"{subject.distroID}/{subject.revision}"
                remote_ref = subject.revision

            LOGGER.info(
                "(%d of %d) Fetching remote ref %s from remote %s",
                num,
                total,
                remote_ref,
                subject.distroID,
            )
            repo.fetch_remote_ref(subject.distroID, local_ref, remote_ref)

            LOGGER.info(
                "(%d of %d) Monitoring Script starting for distro: %s, revision: %s",
                num,
                total,
                subject.distroID,
                remote_ref,
            )
            monitor_subject(subject, repo, local_ref)
