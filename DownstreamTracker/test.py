import os,sys,inspect
import git
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
from UpstreamTracker.MonitorChanges import parseMaintainers,sanitizeFileNames
import Constants.constants as cst

git.Git("C:/Users/ABMARATH/Documents/Work/").clone("git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/bionic",branch = "master")
repo = git.Repo(cst.PathToBionic)

EMPTY_TREE_SHA   = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

#parse maintainers file to get hyperV files
print("[Info] parsing maintainers files")
fileList = parseMaintainers(cst.PathToBionic)
print("[Info] Received HyperV file paths")
fileNames = sanitizeFileNames(fileList)

fifty_first_commits = list(repo.iter_commits('master',paths=fileNames))
print(len(fifty_first_commits))
#print(fifty_first_commits)

for commit in fifty_first_commits:
    parent = commit.parents[0] if commit.parents else EMPTY_TREE_SHA

    diffs  = {

        diff.a_path: diff for diff in commit.diff(parent)

    }