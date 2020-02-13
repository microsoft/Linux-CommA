import git
import os
import sys
import inspect
currentdir = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
import Util.Constants as cst  # noqa E402
from UpstreamTracker.ParseData import process_commits  # noqa E402
from DatabaseDriver.PatchDataTable import PatchDataTable  # noqa E402


# TODO if downstream continues to use, move this to Util.py?
def get_hyperv_filenames(repo, revision="master"):
    '''
    This function will parse maintainers file to get hyperV filenames

    repo: The git repository (git.repo object) to find the maintainers file at
    revision: Revision of the git repository to look at
    '''

    print("[Info] Parsing maintainers file to get relevant hyper-v filenames")
    found_hyperv_block = False
    file_names = []
    # repo is bare, so this is how we get content of maintainers file
    maintainers_file_content = repo.git.show("%s:%s" % (revision, cst.MAINTAINERS_FILENAME))

    for line in maintainers_file_content.split('\n'):
        if 'Hyper-V CORE AND DRIVERS' in line:
            found_hyperv_block = True
        if found_hyperv_block and 'F:\t' in line:
            words = line.strip().split()
            file_path = words[-1]
            # We wish to ignore any Documentation file, as those patches are not relevant.
            if file_path is not None and len(file_path) != 0 and "Documentation" not in file_path:
                file_names.append(file_path)
        # Check if we have reached the end of hyperv block
        if found_hyperv_block and line == '':
            break
    return file_names


if __name__ == '__main__':
    print("Welcome to Patch tracker!!")
    print("Starting patch scraping from files..")
    db = PatchDataTable()
    path_to_linux = os.path.join(cst.PATH_TO_REPOS, cst.LINUX_REPO_NAME)
    if os.path.exists(path_to_linux):
        print("[Info] Path to Linux Repo exists")
        repo = git.Repo(path_to_linux)
        print("[Info] Fetching recent changes")
        repo.git.fetch()
    else:
        print("[Info] Path to Linux repo does not exists. Cloning linux repo.")
        # TODO add functionality for multiple upstream repos (namely linux-next, linux-mainstream, and linux-stable)
        git.Git(cst.PATH_TO_REPOS).clone("https://github.com/torvalds/linux.git", "--bare")
        repo = git.Repo(path_to_linux)

    print("[Info] Parsing maintainers files")
    filenames = get_hyperv_filenames(repo)
    print("[Info] Received HyperV file paths")

    # TODO Make last sha work, get last sha given repo+reference we have
    # if os.path.exists(cst.PATH_TO_LAST_SHA) and out.split()[0] == open(cst.PATH_TO_LAST_SHA).read():
    #     print("[Info] No new commits found")
    # else:
    print("[Info] New commits found")
    print("[Info] Starting commit parsing")
    # TODO make upstream not have to be a distro
    process_commits(repo, "master", filenames, db)
