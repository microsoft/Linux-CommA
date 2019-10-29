import platform
PathToLinux="../linux"
PathToBionic="../bionic"
PathToClone="../"
PathToCommitLog="../commit-log"
PathToLastsha="../lastSHA"
PathToSecret="../LSG-Secret"
NameMaintainers="MAINTAINERS"
RedirectOp='>' if platform.system() == 'Windows' else '>>'