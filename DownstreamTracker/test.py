import os,sys,inspect
import git
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable
import Constants.constants as cst

repo = git.Repo(cst.PathToBionic)
fifty_first_commits = list(repo.iter_commits('master',paths="arch/x86/include/asm/mshyperv.h,drivers/hid/hid-hyperv.c"))
print(len(fifty_first_commits))
print(fifty_first_commits)

repo.iter_commits()