import git

repo = git.Git('~/PatchTracker/linux')
logInfo = repo.heads.master.log()
print(logInfo)