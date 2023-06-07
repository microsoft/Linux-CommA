# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions for parsing commit objects into patch objects
"""

import logging
from datetime import datetime
from typing import List, Optional, Set

from comma.database.driver import DatabaseDriver
from comma.database.model import PatchData
from comma.util import config
from comma.util.tracking import get_filenames, get_linux_repo


IGNORED_FIELDS = "reported-by:", "signed-off-by:", "reviewed-by:", "acked-by:", "cc:"
LOGGER = logging.getLogger(__name__)


def format_diffs(commit, paths):
    """
    Format diffs from commit object into string
    """

    diffs = []
    # We are ignoring merges so all commits should have a single parent
    for diff in commit.tree.diff(commit.parents[0], paths=paths, create_patch=True):
        if diff.a_path is not None:
            # The patch commit diffs are stored as "(filename1)\n(diff1)\n(filename2)\n(diff2)..."
            lines = "\n".join(
                line
                for line in diff.diff.decode("utf-8").splitlines()
                if line.startswith(("+", "-"))
            )
            diffs.append(f"{diff.a_path}\n{lines}")

    return "\n".join(diffs)


def create_patch(commit, paths) -> PatchData:
    """
    Create patch object from a commit object
    """

    patch: PatchData = PatchData(
        commitID=commit.hexsha,
        author=commit.author.name,
        authorEmail=commit.author.email,
        authorTime=datetime.utcfromtimestamp(commit.authored_date),
        commitTime=datetime.utcfromtimestamp(commit.committed_date),
    )

    description = []
    fixed_patches = []
    for num, line in enumerate(commit.message.splitlines()):
        line = line.strip()  # pylint: disable=redefined-loop-name
        if not num:
            patch.subject = line
            continue

        if line.lower().startswith(IGNORED_FIELDS):
            continue

        description.append(line)

        # Check if this patch fixes other patches
        if line.lower().startswith("fixes:"):
            words = line.split(" ")
            if len(words) > 1:
                fixed_patches.append(words[1])

    patch.description = "\n".join(description)
    patch.fixedPatches = " ".join(fixed_patches)  # e.g. "SHA1 SHA2 SHA3"
    patch.affectedFilenames = " ".join(get_filenames(commit))
    patch.commitDiffs = format_diffs(commit, paths)

    return patch


def process_commits(
    commit_ids: Optional[Set[str]] = None,
    revision: str = "origin/master",
    add_to_database: bool = False,
    since: str = config.since,
) -> List[PatchData]:
    """
    Look at all commits in the given repo and handle based on distro.

    commit_ids: Set of commits to process
    revision: revision we want to see the commits of, or None
    add_to_database: whether or not to add to database (side-effect)
    since: if provided, will only process commits after this commit
    """

    repo = get_linux_repo()
    paths = repo.get_tracked_paths()

    if commit_ids is None:
        # We use `--min-parents=1 --max-parents=1` to avoid both merges and graft commits.
        LOGGER.info("Determining commits from tracked files")
        commits = repo.iter_commits(
            rev=revision,
            paths=paths,
            min_parents=1,
            max_parents=1,
            since=since,
        )
    else:
        # If given a set of commit SHAs, get the commit objects.
        commits = []
        for id_ in commit_ids:
            try:
                commits.append(repo.commit(id_))
            except ValueError:
                LOGGER.warning("Commit '%s' does not exist in the repo! Skipping...", id_)

    LOGGER.info("Starting commit processing...")

    all_patches = []
    num_patches_added = 0
    for num, commit in enumerate(commits, 1):
        # Skip root (initial) commit since it should always be present
        # TODO (Issue 54): This can probably be removed
        if commit.parents:
            LOGGER.debug("Parsing commit %s", commit.hexsha)
            patch: PatchData = create_patch(commit, paths)

            if add_to_database:
                with DatabaseDriver.get_session() as session:
                    if (
                        session.query(PatchData.commitID)
                        .filter_by(commitID=patch.commitID)
                        .one_or_none()
                        is None
                    ):
                        session.add(patch)
                        num_patches_added += 1
            else:
                all_patches.append(patch)

        if not num % 250:
            LOGGER.debug(" %d commits processed...", num)

    if add_to_database:
        LOGGER.info("%d patches added to database.", num_patches_added)

    return all_patches
