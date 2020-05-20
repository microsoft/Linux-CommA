import logging
import pathlib

import git

import Util.Config


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


def get_tracked_paths():
    """
    This function will parse maintainers file to get hyperV filenames

    repo: The git repository (git.repo object) to find the maintainers file at
    revision: Revision of the git repository to look at
    """
    logging.debug("Parsing maintainers files...")
    repo = get_repo()
    found_hyperv_block = False
    paths = []
    maintainers_file_content = repo.git.show("master:MAINTAINERS")

    for line in maintainers_file_content.split("\n"):
        if "Hyper-V CORE AND DRIVERS" in line:
            found_hyperv_block = True
        if found_hyperv_block and "F:\t" in line:
            words = line.strip().split()
            file_path = words[-1]
            # We wish to ignore any Documentation file, as those patches are not relevant.
            if (
                file_path is not None
                and len(file_path) != 0
                and "Documentation" not in file_path
            ):
                paths.append(file_path)
        # Check if we have reached the end of hyperv block
        if found_hyperv_block and line == "":
            break
    logging.debug("Parsed!")
    # TODO: Remove duplicates and validate
    paths.extend(Util.Config.paths_to_track)
    assert paths is not None
    return paths
