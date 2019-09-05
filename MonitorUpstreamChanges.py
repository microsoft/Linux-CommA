import git
import os
from constants import PathToLinux, NameMaintainers

repo = git.Repo(PathToLinux)
repo.remotes.origin.pull()

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

fileList = parseMaintainers()
fileNames = sanitizeFIleNames(fileList)
print(fileNames)
i = 0
currDir = os.getcwd()
os.chdir(PathToLinux)
for file in fileNames:
    i += 1
    command = "git log -p -- "+file+" >> ../commit-log/"+str(i)
    print(command)
    os.system(command)
os.chdir(currDir)