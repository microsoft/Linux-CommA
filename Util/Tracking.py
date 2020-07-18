# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import itertools
import logging
import pathlib
import re
from typing import List, Set

import git

import Util.Config


def get_filenames(commit: git.Commit) -> List[str]:
    if len(commit.parents) == 0:
        return []
    diffs = commit.tree.diff(commit.parents[0])
    # Sometimes a path is in A and not B but we want all filenames.
    a = {diff.a_path for diff in diffs if diff.a_path is not None}
    b = {diff.b_path for diff in diffs if diff.b_path is not None}
    return list(a | b)


def get_repo_path(name: str) -> pathlib.Path:
    return pathlib.Path("Repos", name).resolve()


UPDATED_REPOS = set()


def get_repo(
    name: str,
    url: str = "https://github.com/torvalds/linux.git",
    bare: bool = True,
    shallow: bool = True,
    pull: bool = False,
) -> git.Repo:
    """Clone and optionally update a repo, returning the object.

    By default this clones the Linux repo to 'name' from 'url',
    optionally 'bare', and returns the 'git.Repo' object. It only
    fetches or pulls once per session, and only if told to do so.
    """
    global UPDATED_REPOS
    repo = None
    path = get_repo_path(name)
    if path.exists():
        repo = git.Repo(path)
        if name not in UPDATED_REPOS:
            if pull:
                logging.info(f"Pulling '{name}' repo...")
                repo.remotes.origin.pull()
                logging.info("Pulled!")
            elif Util.Config.fetch:
                logging.info(f"Fetching '{name}' repo...")
                repo.git.fetch(
                    "--all",
                    "--tags",
                    "--force",
                    f"--shallow-since={Util.Config.since}",
                )
                logging.info("Fetched!")
    else:
        logging.info(f"Cloning '{name}' repo from '{url}'...")
        args = {"bare": bare}
        if shallow:
            args.update({"shallow_since": Util.Config.since})
        repo = git.Repo.clone_from(url, path, **args)
        logging.info("Cloned!")
    # We either cloned, pulled, fetched, or purposefully skipped doing
    # so. Don't update the repo again this session.
    UPDATED_REPOS.add(name)
    return repo


LINUX_REPO: git.Repo = None


def get_linux_repo() -> git.Repo:
    global LINUX_REPO
    if LINUX_REPO is None:
        LINUX_REPO = get_repo("linux.git")
    return LINUX_REPO


def get_files(section: str, content: List[str]) -> Set[str]:
    """Get list of files under section.

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
    # Drop until we reach start of section.
    content = itertools.dropwhile(lambda x: section not in x, content)
    # Take until we reach end of section.
    content = itertools.takewhile(lambda x: x.strip() != "", content)
    # Extract file paths from section.
    paths = {x.strip().split()[-1] for x in content if x.startswith("F:")}
    # Drop Documentation and return everything else.
    return {x for x in paths if not x.startswith("Documentation")}


TRACKED_PATHS: List[str] = None


def get_tracked_paths(sections=Util.Config.sections) -> List[str]:
    """Get list of files from MAINTAINERS for given sections."""
    global TRACKED_PATHS
    if TRACKED_PATHS is not None:
        return TRACKED_PATHS
    logging.debug("Parsing MAINTAINERS file...")
    repo = get_linux_repo()
    paths = set()
    # All tag commits starting with v4, also master.
    tags = repo.git.tag("v[^123]*", list=True).split()
    commits = [c for c in tags if re.match(r"v[0-9]+\.[0-9]+$", c)]
    commits.append("master")
    for commit in commits:
        maintainers = repo.git.show(f"{commit}:MAINTAINERS").split("\n")
        for section in sections:
            paths |= get_files(section, maintainers)
    logging.debug("Parsed!")
    TRACKED_PATHS = sorted(paths)
    return TRACKED_PATHS


def print_tracked_paths():
    for path in get_tracked_paths():
        print(path)
