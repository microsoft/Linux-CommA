# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions and classes for fetching and parsing data from Git
"""

import logging
import pathlib
import re
from typing import Any, Iterable, List, Optional, Set, Tuple

import git

from comma.util import config


LOGGER = logging.getLogger(__name__)


def get_filenames(commit: git.Commit) -> List[str]:
    """
    Get all paths affected by a given commit
    """

    if commit.parents:
        return []
    diffs = commit.tree.diff(commit.parents[0])
    # Sometimes a path is in A and not B but we want all filenames.
    return list(
        {diff.a_path for diff in diffs if diff.a_path is not None}
        | {diff.b_path for diff in diffs if diff.b_path is not None}
    )


class Repo:
    """
    Common repository operations
    Wraps git.Repo, so unimplemented methods are passed to self.obj
    """

    def __init__(self, name: str, url: str) -> None:
        self.name: str = name
        self.url: str = url
        self.path = path = pathlib.Path("Repos", name).resolve()
        self.obj: Optional[git.Repo] = git.Repo(path) if path.exists() else None
        self._tracked_paths: Optional[tuple] = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self.obj, name)

    def fetch(self, repack: bool = False):
        """Fetch repo"""

        if repack:
            LOGGER.info("Repacking '%s' repo", self.name)
            self.obj.git.repack("-d")

        LOGGER.info("Fetching '%s' repo since %s", self.name, config.since)
        try:
            self.obj.remotes.origin.fetch(
                shallow_since=config.since,
                verbose=True,
                progress=GitProgressPrinter(),
            )
            LOGGER.info("Completed fetching %s", self.name)
        except git.GitCommandError as e:
            # Sometimes a shallow-fetched repo will need repacking before fetching again
            if "fatal: error in object: unshallow" in e.stderr and not repack:
                LOGGER.warning("Error with shallow clone. Repacking before retrying.")
                self.fetch(repack=True)
            else:
                raise

    def clone(self, shallow: bool = True):
        """Clone repo"""

        LOGGER.info("Cloning '%s' repo from '%s'.", self.name, self.url)
        args = {"shallow_since": config.since} if shallow else {}
        self.obj = git.Repo.clone_from(self.url, self.path, **args, progress=GitProgressPrinter())
        LOGGER.info("Completed cloning %s", self.name)

    def pull(self):
        """Pull repo"""
        LOGGER.info("Pulling '%s' repo.", self.name)
        self.obj.remotes.origin.pull(progress=GitProgressPrinter())
        LOGGER.info("Completed pulling %s", self.name)

    @property
    def exists(self):
        """Convenience property to see if repo abject has been populated"""
        return self.obj is not None

    def get_tracked_paths(self, sections=config.sections) -> Tuple[str]:
        """Get list of files from MAINTAINERS for given sections."""

        if self._tracked_paths is not None:
            return self._tracked_paths

        LOGGER.debug("Parsing MAINTAINERS file for %s", self.name)
        paths = set()

        # All tags starting with v4, also master.
        refs = [
            tag
            for tag in self.obj.git.tag("v[^123]*", list=True).split()
            if re.match(r"v\d+\.+$", tag)
        ]
        refs.append("origin/HEAD")  # Include default branch (Usually master or main)

        for ref in refs:
            paths |= extract_paths(sections, self.obj.git.show(f"{ref}:MAINTAINERS"))

        LOGGER.debug("Completed parsing MAINTAINERS file for %s", self.name)
        self._tracked_paths = tuple(sorted(paths))

        return self._tracked_paths


class Session:
    """
    Container for session data to avoid duplicate actions
    """

    def __init__(self) -> None:
        self.repos: dict = {}

    def get_repo(
        self,
        name: str,
        url: str,
        shallow: bool = True,
        pull: bool = False,
    ) -> Repo:
        """
        Clone and optionally update a repo, returning the object.

        Only clones, fetches, or pulls once per session
        """

        if name in self.repos:
            # Repo has been cloned, fetched, or pulled already in this session
            return self.repos[name]

        repo = self.repos[name] = Repo(name, url)
        if not repo.exists:
            # No local repo, clone from source
            repo.clone(shallow)

        elif pull:
            repo.pull()
        else:
            repo.fetch()

        return repo


# TODO (Issue 56): Move session creation to main program logic
SESSION = Session()


def get_linux_repo(
    name: str = "linux.git",
    url: str = "https://github.com/torvalds/linux.git",
    shallow: bool = True,
    pull: bool = False,
) -> Repo:
    """
    Shortcut for getting Linux repo
    """

    return SESSION.get_repo(name, url, shallow=shallow, pull=pull)


def extract_paths(sections: Iterable, content: str) -> Set[str]:
    # pylint: disable=wrong-spelling-in-docstring
    """
    Get set of files under the given sections.

    The MAINTAINERS file sections look like:

    Hyper-V CORE AND DRIVERS
    M:	"K. Y. Srinivasan" <kys@microsoft.com>
    ...
    F:	Documentation/ABI/stable/sysfs-bus-vmbus
    F:	arch/x86/hyperv
    F:	drivers/clocksource/hyperv_timer.c
    F:	drivers/hv/
    ...
    F:	tools/hv/

    Each section ends with a blank line.
    """

    remaining = set(sections)
    in_section = False
    paths = set()
    for line in content.splitlines():
        if in_section:
            # Section ends with a blank line
            if not line.strip():
                in_section = False

                # If there are no more sections, end now
                if not remaining:
                    break

            # Extract Paths
            if line.startswith("F:"):
                path = line.strip().split(maxsplit=1)[-1]

                # Skip Documentation
                if not path.startswith("Documentation"):
                    paths.add(path)

        # Look for start of a section
        elif current := next((section for section in remaining if section in line), None):
            in_section = True
            remaining.remove(current)

    return paths


class GitProgressPrinter(git.RemoteProgress):
    """
    Simple status printer for GitPython
    """

    def update(self, op_code, cur_count, max_count=None, message=""):
        """
        Subclassed from parent. Called for each line in output.
        """
        if not config.verbose:
            return

        print(f"  {self._cur_line}", end="    ")
        if op_code & self.END:
            print()
        else:
            print("\r", end="", flush=True)
