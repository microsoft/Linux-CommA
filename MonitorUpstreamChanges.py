import git
import os
from constants import *

os.makedirs(os.path.dirname(PathToCommitLog), exist_ok=True)
if os.path.exists(PathToLinux):
    print("[Info] Path to Linux Repo exists")
    repo = git.Repo(PathToLinux)
    print("[Info] Pulling recent changes")
    repo.remotes.origin.pull()
    print("[Info] Git pull complete")
else:
    print("[Info] Path to Linux repo does not exists")
    print("[Info] Cloning linux repo")
    git.Git(PathToCloneLinux).clone("https://github.com/torvalds/linux.git")
    print("[Info] Cloning Complete")
def parseMaintainers():
    found_hyperv_block = False
    found_files = False
    fileNames = []
    with open (PathToLinux+"/"+NameMaintainers,'r', encoding="utf8") as maintainers:
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

def sanitizeFIleNames(fileNames):
    '''
    Remove Documentation files
    Add all the file paths in from folder path
    '''
    newList = []
    for fileName in fileNames:
        if 'Documentation' in fileName:
            continue
        elif os.path.isdir(PathToLinux+"/"+fileName):
            listDir = os.listdir(PathToLinux+"/"+fileName)
            for file in listDir:
                if fileName[-1:] == '/':
                    newList.append(fileName+""+file)
                else:
                    newList.append(fileName+"/"+file)  
        else:
            newList.append(fileName)
    return newList

print("[Info] parsing maintainers files")
fileList = parseMaintainers()
print("[Info] Received HyperV file paths")
fileNames = sanitizeFIleNames(fileList)
print("[Info] Preprocessed HyperV file paths")
# print(fileNames)
i = 0
currDir = os.getcwd()
os.chdir(PathToLinux)
# print(' '.join(fileNames))
command = "git log -p -- "+' '.join(fileNames)+" >> ../commit-log/log"
os.system(command)
print("[Info] Created HyperV files git logs at "+PathToCommitLog)
os.chdir(currDir)