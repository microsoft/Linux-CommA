import subprocess
import os
# import git

# repo = git.Git('~/PatchTracker/linux')
# logInfo = repo.heads.master.log()
# print(logInfo)
currDir = os.getcwd()
with open ('hyperVfiles.txt','r') as fileList:
    os.chdir("../linux")
    os.system("git pull")
    for hyperVfile in fileList:
        #myCommand = os.popen("git log -p -- "+hyperVfile).read()
        # commits = subprocess.Popen(['git','log','-p','--',hyperVfile],
                                   # stdout=subprocess.PIPE,
                                   # stderr=subprocess.STDOUT)
        #stdout, stderr = commits.communicate()
        #print(stdout)
        # print(stderr)
        i = 0
        os.system("git log -p -- "+hyperVfile+" >> ../commit-log/1.log")
        i += 1
        print(i)
        break

fileList.closed
