import platform
PathToLinux="../linux"
PathToBionic="../bionic"
PathToClone="../"
PathToCommitLog="../commit-log"
PathToLastsha="../lastSHA"
PathToSymbols="../Symbols"
PathToSecret="../LSG-Secret"
NameMaintainers="MAINTAINERS"
RedirectOp='>>' if platform.system() == 'Windows' else '>'