# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Operations for downstream targets
"""

import logging
from functools import cached_property

from comma.database.model import (
    Distros,
    MonitoringSubjects,
    MonitoringSubjectsMissingPatches,
    PatchData,
)
from comma.downstream.matcher import patch_matches
from comma.util.tracking import get_linux_repo


LOGGER = logging.getLogger(__name__.split(".", 1)[0])


class Downstream:
    """
    Parent object for downstream operations
    """

    def __init__(self, config, database) -> None:
        self.config = config
        self.database = database

    @cached_property
    def repo(self):
        """
        Get repo when first accessed
        """
        return get_linux_repo(since=self.config.upstream_since)

    def monitor(self):
        """
        Cycle through downstream remotes and search for missing commits
        """

        repo = self.repo

        # Add repos as a remote if not already added
        with self.database.get_session() as session:
            for distro_id, url in session.query(Distros.distroID, Distros.repoLink).all():
                # Skip Debian for now
                if distro_id not in self.repo.remotes and not distro_id.startswith("Debian"):
                    LOGGER.debug("Adding remote %s from %s", distro_id, url)
                    repo.create_remote(distro_id, url=url)

        # Update stored revisions for repos as appropriate
        LOGGER.info("Updating tracked revisions for each repo.")
        with self.database.get_session() as session:
            for (distro_id,) in session.query(Distros.distroID).all():
                self.update_tracked_revisions(distro_id)

        with self.database.get_session() as session:
            subjects = session.query(MonitoringSubjects).all()
            total = len(subjects)

            for num, subject in enumerate(subjects, 1):
                if subject.distroID.startswith("Debian"):
                    # TODO (Issue 51): Don't skip Debian
                    LOGGER.info("(%d of %d) Skipping %s", num, total, subject.distroID)
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
                repo.fetch_remote_ref(
                    subject.distroID, local_ref, remote_ref, since=self.config.downstream_since
                )

                LOGGER.info(
                    "(%d of %d) Monitoring Script starting for distro: %s, revision: %s",
                    num,
                    total,
                    subject.distroID,
                    remote_ref,
                )
                self.monitor_subject(subject, local_ref)

    def monitor_subject(self, monitoring_subject, reference: str):
        """
        Update the missing patches in the database for this monitoring_subject

        monitoring_subject: The MonitoringSubject we are updating
        reference: Git reference to monitor
        """

        missing_cherries = self.repo.get_missing_cherries(
            reference,
            self.repo.get_tracked_paths(self.config.upstream.sections),
            since=self.config.upstream_since,
        )
        LOGGER.debug("Found %d missing patches through cherry-pick.", len(missing_cherries))

        # Run extra checks on these missing commits
        missing_patch_ids = self.get_missing_patch_ids(missing_cherries, reference)
        LOGGER.info("Identified %d missing patches", len(missing_patch_ids))

        # Delete patches that are no longer missing.
        # NOTE: We do this in separate sessions in order to cleanly expire their objects and commit
        # the changes to the database. There is surely another way to do this, but it works.
        subject_id = monitoring_subject.monitoringSubjectID
        with self.database.get_session() as session:
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
        with self.database.get_session() as session:
            patches = session.query(MonitoringSubjectsMissingPatches).filter_by(
                monitoringSubjectID=subject_id
            )
            new_missing_patches = 0
            for patch_id in missing_patch_ids:
                # Only add if it doesn't already exist. We're dealing with patches on the scale
                # of 100, so the number of queries and inserts here doesn't matter.
                if patches.filter_by(patchID=patch_id).first() is None:
                    new_missing_patches += 1
                    session.add(
                        MonitoringSubjectsMissingPatches(
                            monitoringSubjectID=subject_id, patchID=patch_id
                        )
                    )
            LOGGER.info("Adding %d patches that are now missing.", new_missing_patches)

    def get_missing_patch_ids(self, missing_cherries, reference):
        """
        Attempt to determine which patches are missing from a list of missing cherries
        """

        paths = self.repo.get_tracked_paths(self.config.upstream.sections)

        with self.database.get_session() as session:
            patches = (
                session.query(PatchData)
                .filter(PatchData.commitID.in_(missing_cherries))
                .order_by(PatchData.commitTime)
                .all()
            )
            if not patches:
                return []

            # We only want to check downstream patches as old as the oldest upstream missing patch
            earliest_commit_date = min(patch.commitTime for patch in patches).isoformat()
            LOGGER.debug("Processing commits since %s", earliest_commit_date)

            # Get the downstream commits for this revision (these are distinct from upstream because
            # they have been cherry-picked). This is slow but necessary!

            LOGGER.info("Determining downstream commits from tracked files")
            # We use `--min-parents=1 --max-parents=1` to avoid both merges and graft commits
            downstream_patches = tuple(
                PatchData.create(commit, paths)
                for commit in self.repo.iter_commits(
                    rev=reference,
                    paths=paths,
                    min_parents=1,
                    max_parents=1,
                    since=earliest_commit_date,
                )
            )

            # Double check the missing cherries using our fuzzy algorithm.
            LOGGER.info("Starting confidence matching for %d upstream patches...", len(patches))
            missing_patches = [
                p.patchID for p in patches if not patch_matches(downstream_patches, p)
            ]

        return missing_patches

    def update_tracked_revisions(self, distro_id):
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
                for tag in self.repo.get_remote_tags(distro_id)
                if "azure" in tag and all(label not in tag for label in ("edge", "cvm", "fde"))
            )
            self.database.update_revisions_for_distro(distro_id, tag_names[-2:])
