# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions and classes for fetching and parsing data from Git
"""

import functools
import logging
import pathlib
import re
from typing import Iterable, List, Set

import git

from comma.util import config


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
    ) -> git.Repo:
        """Clone and optionally update a repo, returning the object.

        By default this clones the Linux repo to 'name' from 'url', and returns the 'git.Repo'
        object. It only fetches or pulls once per session, and only if told to do so.
        """

        path = pathlib.Path("Repos", name).resolve()
        if not path.exists():
            # No local repo, clone from source
            return self.clone_repo(name, path=path, url=url, shallow=shallow)

        if name in self.repos:
            # Repo has been cloned, fetched, or pulled already in this session
            return self.repos[name]

        repo = self.repos[name] = git.Repo(path)
        if pull:
            logging.info("Pulling '%s' repo.", name)
            repo.remotes.origin.pull(progress=GitProgressPrinter())
            logging.info("Completed pulling %s", name)
        else:
            self.fetch_repo(name, repo)

        return repo

    def fetch_repo(self, name: str, repo: git.Repo, repack: bool = False):
        """Fetch an existing repo"""

        if repack:
            logging.info("Repacking '%s' repo", name)
            repo.git.repack("-d")

        logging.info("Fetching '%s' repo since %s", name, config.since)
        try:
            repo.remotes.origin.fetch(
                shallow_since=config.since,
                verbose=True,
                progress=GitProgressPrinter(),
            )
            logging.info("Completed fetching %s", name)
        except git.GitCommandError as e:
            # Sometimes a shallow-fetched repo will need repacking before fetching again
            if "fatal: error in object: unshallow" in e.stderr and not repack:
                logging.warning("Error with shallow clone. Repacking before retrying.")
                self.fetch_repo(name, repo=repo, repack=True)
            else:
                raise

    def clone_repo(self, name: str, path: pathlib.Path, url: str, shallow: bool = True):
        """Clone a repo from the given url"""

        logging.info("Cloning '%s' repo from '%s'.", name, url)
        args = {"shallow_since": config.since} if shallow else {}
        self.repos[name] = git.Repo.clone_from(url, path, **args, progress=GitProgressPrinter())
        logging.info("Completed cloning %s", name)
        return self.repos[name]


# TODO: Move session creation to main program logic
SESSION = Session()


def get_linux_repo(
    name: str = "linux.git",
    url: str = "https://github.com/torvalds/linux.git",
    shallow: bool = True,
    pull: bool = False,
) -> git.Repo:
    """
    Shortcut for getting linux repo
    """

    return SESSION.get_repo(name, url, shallow=shallow, pull=pull)


def extract_paths(sections: Iterable, content: str) -> Set[str]:
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


@functools.cache
def get_tracked_paths(sections=config.sections) -> List[str]:
    """Get list of files from MAINTAINERS for given sections."""

    logging.debug("Parsing MAINTAINERS file...")
    repo = get_linux_repo()
    paths = set()

    # All tags starting with v4, also master.
    refs = [
        tag for tag in repo.git.tag("v[^123]*", list=True).split() if re.match(r"v\d+\.+$", tag)
    ]
    refs.append("origin/master")

    for ref in refs:
        paths |= extract_paths(sections, repo.git.show(f"{ref}:MAINTAINERS"))

    logging.debug("Parsed!")
    return sorted(paths)


def print_tracked_paths():
    """
    Utility function for printing tracked paths
    """

    for path in get_tracked_paths():
        print(path)


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
