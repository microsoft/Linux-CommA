# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import itertools
import logging
import pathlib
from typing import List

import git

import Util.Config


def get_filenames(commit: git.Commit):
    if len(commit.parents) == 0:
        return []
    diffs = commit.tree.diff(commit.parents[0])
    # Sometimes a path is in A and not B but we want all filenames.
    a = {diff.a_path for diff in diffs if diff.a_path is not None}
    b = {diff.b_path for diff in diffs if diff.b_path is not None}
    return list(a | b)


def get_repo_path(name: str) -> pathlib.Path:
    return pathlib.Path("Repos", name).resolve()


# Global state tracking for repos which have been updated.
updated_repos = set()


def get_repo(
    name="linux.git",
    url="https://github.com/torvalds/linux.git",
    bare=True,
    shallow=True,
    pull=False,
) -> git.Repo:
    """Clone and optionally update a repo, returning the object.

    By default this clones the Linux repo to 'name' from 'url',
    optionally 'bare', and returns the 'git.Repo' object. It only
    fetches or pulls once per session, and only if told to do so.
    """
    repo = None
    path = get_repo_path(name)
    if path.exists():
        repo = git.Repo(path)
        if name not in updated_repos:
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
    updated_repos.add(name)
    return repo


def get_files(section: str, content: List[str]) -> List[str]:
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
    paths = [x.strip().split()[-1] for x in content if x.startswith("F:")]
    # Drop Documentation and return everything else.
    return [x for x in paths if not x.startswith("Documentation")]


def get_tracked_paths(sections=Util.Config.sections):
    """Get list of files from MAINTAINERS for given sections.

    """
    logging.debug("Parsing MAINTAINERS file...")
    repo = get_repo()
    paths = []
    # TODO: Run those over several revisions bisecting the last few
    # years of history and then deduplicate the paths, that way we
    # don't miss anything.
    maintainers = repo.git.show("master:MAINTAINERS").split("\n")
    for section in sections:
        paths += get_files(section, maintainers)
    logging.debug("Parsed!")
    return paths


def print_tracked_paths():
    for path in get_tracked_paths():
        print(path)
