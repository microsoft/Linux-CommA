import platform

PATH_TO_REPOS = "Repos"
LINUX_REPO_URL = "https://github.com/torvalds/linux.git"
LINUX_REPO_NAME = "linux.git"
MAINTAINERS_FILENAME = "MAINTAINERS"
PATH_TO_LAST_SHA = "../lastSHA"
LINUX_SYMBOL_REPO_NAME = "linux-sym"

RedirectOp = ">>" if platform.system() == "Windows" else ">"
