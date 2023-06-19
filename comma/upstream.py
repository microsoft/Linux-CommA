# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions for parsing commit objects into patch objects
"""

import logging
from functools import cached_property

from comma.database.model import PatchData
from comma.util.tracking import get_linux_repo


LOGGER = logging.getLogger(__name__)


class Upstream:
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

    def process_commits(self):
        """
        Generate patches for commits affecting tracked paths
        """

        paths = self.repo.get_tracked_paths(self.config.sections)
        added = 0
        total = 0

        # We use `--min-parents=1 --max-parents=1` to avoid both merges and graft commits.
        LOGGER.info("Determining upstream commits from tracked files")
        for commit in self.repo.iter_commits(
            rev="origin/master",
            paths=paths,
            min_parents=1,
            max_parents=1,
            since=self.config.upstream_since,
        ):
            total += 1
            with self.database.get_session() as session:
                # See if commit ID is in database
                if (
                    session.query(PatchData.commitID)
                    .filter_by(commitID=commit.hexsha)
                    .one_or_none()
                    is None
                ):
                    session.add(PatchData.create(commit, paths))
                    added += 1

        LOGGER.info("%d of %d patches added to database.", added, total)
