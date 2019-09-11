import git

import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from UpstreamTracker.ParseData import getEachPatch
import subprocess




def parseMaintainers(PathLinux):
    '''
    This function will parse maintainers file to get hyperV filenames
    '''
    found_hyperv_block = False
    found_files = False
    fileNames = []
    with open (PathLinux+"/"+cst.NameMaintainers,'r', encoding="utf8") as maintainers:
        for line in maintainers:
            if 'Hyper-V CORE AND DRIVERS' in line:
                found_hyperv_block = True
            if found_hyperv_block and 'F:\t' in line:
                files = line.strip().split()
                lastPart = ''.join(files[-1:])
                found_files = True
                if lastPart is not None or len(lastPart) != 0:
                    fileNames.append(lastPart)
            if found_files and line == '\n':
                break
    return  fileNames         

def sanitizeFileNames(fileNames):
    '''
    Remove Documentation files
    Add all the file paths in from folder path
    '''
    newList = []
    for fileName in fileNames:
        if 'Documentation' in fileName:
            continue
        elif os.path.isdir(cst.PathToLinux+"/"+fileName):
            listDir = os.listdir(cst.PathToLinux+"/"+fileName)
            for file in listDir:
                if fileName[-1:] == '/':
                    newList.append(fileName+""+file)
                else:
                    newList.append(fileName+"/"+file)  
        else:
            newList.append(fileName)
    return newList

if __name__ == '__main__':
    print("Welcome to Patch tracker!!")
    os.makedirs(os.path.dirname(cst.PathToCommitLog), exist_ok=True)
    if os.path.exists(cst.PathToLinux):
        print("[Info] Path to Linux Repo exists")
        repo = git.Repo(cst.PathToLinux)
        print("[Info] Pulling recent changes")
        repo.remotes.origin.pull()
        print("[Info] Git pull complete")
    else:
        print("[Info] Path to Linux repo does not exists")
        print("[Info] Cloning linux repo")
        git.Git(cst.PathToClone).clone("https://github.com/torvalds/linux.git")
        print("[Info] Cloning Complete")

    print("[Info] parsing maintainers files")
    fileList = parseMaintainers(cst.PathToLinux)
    print("[Info] Received HyperV file paths")
    fileNames = sanitizeFIleNames(fileList)
    print("[Info] Preprocessed HyperV file paths")
    # print(fileNames)
    i = 0
    currDir = os.getcwd()
    os.chdir(cst.PathToLinux)
    # print(' '.join(fileNames))
    command = "git log -p -- "+' '.join(fileNames)+" >> ../commit-log/log"
    os.system(command)
    print("[Info] Created HyperV files git logs at "+cst.PathToCommitLog)


    out = subprocess.getoutput("git rev-parse origin/master")

    if out.split()[0] == open(cst.PathToLastsha).read():
        print("[Info] No new commits found")
    else:
        print("[Info] New commits found")
        gitCommand = "git rev-parse origin/master >>"+cst.PathToLastsha
        os.system(gitCommand)
        print("[Info] Starting commit parsing")
        getEachPatch(cst.PathToCommitLog+"/log")

    os.chdir(currDir)