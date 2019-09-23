import git
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from UpstreamTracker.MonitorChanges import parseMaintainers,sanitizeFileNames
from Objects.UpstreamPatch import UpstreamPatch
from Objects.DistroPatchMatch import DistroPatchMatch
from Objects.UbuntuPatch import Ubuntu_Patch
from datetime import datetime
from DatabaseDriver.DistroMatch import DistroMatch
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable
from DownstreamTracker.DownstreamMatcher import DownstreamMatcher
from DatabaseDriver.DistroTable import DistroTable
from UpstreamTracker.ParseData import parse_log

def monitor_distro(distro):
    # make sure that Kernel is present
    print(distro.distro_id+" Monitoring Script..")
    folder_name = distro.repo_link.rsplit('/', 1)[-1]
    print(folder_name)
    if os.path.exists(cst.PathToClone+folder_name):
        print("[Info] Path to Ubuntu Bionic Repo exists")
        repo = git.Repo(cst.PathToClone+folder_name)
        print("[Info] Pulling recent changes")
        repo.remotes.origin.pull()
        print("[Info] Git pull complete")
    else:
        print("[Info] Path to Ubuntu Bionic does not exists")
        print("[Info] Cloning Ubuntu Bionic repo")
        git.Git(cst.PathToClone).clone(distro.repo_link)
        print("[Info] Cloning Complete")


    #parse maintainers file to get hyperV files
    print("[Info] parsing maintainers files")
    fileList = parseMaintainers(cst.PathToClone+folder_name)
    print("[Info] Received HyperV file paths")
    fileNames = sanitizeFileNames(fileList)


    # Collecting git logs for HyperV files
    print("[Info] Preprocessed HyperV file paths")
    currDir = os.getcwd()
    os.chdir(cst.PathToClone+folder_name)
    command = "git log -p -- "+' '.join(fileNames)+" > "+cst.PathToCommitLog+"/"+folder_name+"Log"
    os.system(command)
    print("[Info] Created HyperV files git logs at "+cst.PathToCommitLog+"/"+folder_name+"Log")

    # Parse git log and dump data into database
    match = DownstreamMatcher(UpstreamPatchTable())
    parse_log(cst.PathToCommitLog+"/"+folder_name+"Log", DistroMatch(), match, distro, distro.distro_id)
    os.chdir(currDir)

if __name__ == '__main__':
    print("Welcome to Patch tracker!!")

    # connect to DB read all entries in Distro table
    Distro_table = DistroTable()
    distro_list = Distro_table.get_distro_list()

    os.makedirs(os.path.dirname(cst.PathToCommitLog), exist_ok=True)

    # for every distro run next
    for distro in distro_list:
        monitor_distro(distro)


    
