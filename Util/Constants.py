import platform
PATH_TO_REPOS = "Repos"
LINUX_REPO_NAME = "linux.git"
SECRET_REPO_NAME = "LSG-Secret"
MAINTAINERS_FILENAME = "MAINTAINERS"
PATH_TO_LAST_SHA = "../lastSHA"
LINUX_SYMBOL_REPO_NAME = "linux-sym"

UPSTREAM_TABLE_NAME = "PatchData"
DOWNSTREAM_TABLE_NAME = "MonitoringSubjectsMissingPatches"
DISTROS_TABLE_NAME = "Distros"
MONITORING_SUBJECTS_TABLE_NAME = "MonitoringSubjects"

PathToSymbols = "../Symbols"
RedirectOp = '>>' if platform.system() == 'Windows' else '>'
