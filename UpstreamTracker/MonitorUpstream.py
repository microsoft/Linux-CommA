import logging
import os

import git

import Util.Constants as cst
from UpstreamTracker.ParseData import process_commits
from Util.Config import filepaths_to_track


def get_hyperv_filenames(repo, revision="master"):
    """
    This function will parse maintainers file to get hyperV filenames

    repo: The git repository (git.repo object) to find the maintainers file at
    revision: Revision of the git repository to look at
    """
    logging.debug("Parsing maintainers file to get relevant hyper-v filenames")
    found_hyperv_block = False
    file_names = []
    # repo is bare, so this is how we get content of maintainers file
    maintainers_file_content = repo.git.show(
        "%s:%s" % (revision, cst.MAINTAINERS_FILENAME)
    )

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
                file_names.append(file_path)
        # Check if we have reached the end of hyperv block
        if found_hyperv_block and line == "":
            break
    logging.debug("Parsing maintainers file done")
    # TODO: Remove duplicates and Validate
    file_names.extend(filepaths_to_track)
    logging.debug("Merge config filepaths")
    return file_names


def monitor_upstream():
    logging.info("Starting patch scraping from files..")
    path_to_linux = os.path.join(cst.PATH_TO_REPOS, cst.LINUX_REPO_NAME)
    if os.path.exists(path_to_linux):
        logging.debug("Path to Linux Repo exists")
        repo = git.Repo(path_to_linux)
        logging.debug("Fetching recent changes")
        repo.git.fetch()
    else:
        logging.debug("Path to Linux repo does not exists. Cloning linux repo.")
        # TODO add functionality for multiple upstream repos (namely linux-next, linux-mainstream, and linux-stable)
        git.Git(cst.PATH_TO_REPOS).clone(
            "https://github.com/torvalds/linux.git", "--bare"
        )
        repo = git.Repo(path_to_linux)

    logging.debug("Parsing maintainers files to get hyperV filenames")
    filenames = get_hyperv_filenames(repo)
    logging.info("Received HyperV file paths")

    # TODO Make last sha work, get last sha given repo+reference we have
    # if os.path.exists(cst.PATH_TO_LAST_SHA) and out.split()[0] == open(cst.PATH_TO_LAST_SHA).read():
    #     print("[Info] No new commits found")
    # else:
    #     print("[Info] New commits found")
    logging.debug("Starting commit parsing")
    process_commits(repo, "master", filenames, add_to_database=True)
