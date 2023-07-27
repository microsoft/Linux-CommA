# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions for parsing commit objects into patch objects
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from comma.database.model import PatchData


if TYPE_CHECKING:
    from comma.cli import Session


LOGGER = logging.getLogger(__name__)


class Upstream:
    """
    Parent object for downstream operations
    """

    def __init__(self, session: Session) -> None:
        self.config = session.config
        self.database = session.database
        self.repo = session.repo
        self.session = session

    def process_commits(self, force_update=False):
        """
        Generate patches for commits affecting tracked paths
        """

        paths = self.session.get_tracked_paths()
        added = 0
        updated = 0
        total = 0

        # We use `--min-parents=1 --max-parents=1` to avoid both merges and graft commits.
        LOGGER.info("Determining upstream commits from tracked files")
        for commit in self.repo.iter_commits(
            rev=f"origin/{self.config.upstream.reference}",
            paths=paths,
            min_parents=1,
            max_parents=1,
            since=self.config.upstream_since,
        ):
            total += 1
            with self.database.get_session() as session:
                # Query database for commit
                if force_update:
                    query = session.query(PatchData)
                else:
                    query = session.query(PatchData.commitID)
                patch = query.filter_by(commitID=commit.hexsha).one_or_none()

                # If commit is missing, add it
                if patch is None:
                    session.add(PatchData.create(commit, paths))
                    added += 1

                # If commit is present, optionally update
                elif force_update:
                    # Get a local patch object
                    patch_data = PatchData.create(commit, paths)

                    # Iterate through the columns
                    record_updated = False
                    for column in (
                        col.name for col in patch_data.__table__.columns if not col.primary_key
                    ):
                        # Skip commit ID
                        if column == "commitID":
                            continue

                        # If the new value is different, update it
                        new_value = getattr(patch_data, column)
                        if getattr(patch, column) != new_value:
                            LOGGER.info("Updating %s for %s", column, commit.hexsha)
                            setattr(patch, column, new_value)
                            record_updated = True

                    if record_updated:
                        updated += 1

        LOGGER.info("%d of %d patches added to database.", added, total)
        if force_update:
            LOGGER.info("%d of %d patches updated in database.", updated, total)
