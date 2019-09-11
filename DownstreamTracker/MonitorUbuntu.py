import git
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from UpstreamTracker.MonitorChanges import parseMaintainers,sanitizeFIleNames



if __name__ == '__main__':
    print("Welcome to Patch tracker!!")
    os.makedirs(os.path.dirname(cst.PathToCommitLog), exist_ok=True)
    print("..Ubuntu Monitoring Script..")
    if os.path.exists(cst.PathToBionic):
        print("[Info] Path to Ubuntu Bionic Repo exists")
        repo = git.Repo(cst.PathToLinux)
        print("[Info] Pulling recent changes")
        repo.remotes.origin.pull()
        print("[Info] Git pull complete")
    else:
        print("[Info] Path to Ubuntu Bionic does not exists")
        print("[Info] Cloning Ubuntu Bionic repo")
        git.Git(cst.PathToClone).clone("git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/bionic")
        print("[Info] Cloning Complete")

    print("[Info] parsing maintainers files")
    fileList = parseMaintainers(cst.PathToBionic)
    print("[Info] Received HyperV file paths")
    fileNames = sanitizeFileNames(fileList)
    print("[Info] Preprocessed HyperV file paths")
    print(fileNames)
    currDir = os.getcwd()
    os.chdir(cst.PathToBionic)
    # print(' '.join(fileNames))
    command = "git log -p -- "+' '.join(fileNames)+" >> ../commit-log/log"
    os.system(command)
    print("[Info] Created HyperV files git logs at "+cst.PathToCommitLog)