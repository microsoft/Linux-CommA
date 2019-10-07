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

def monitor_distro(distro, kernel_list):
    currDir = os.getcwd()
    try:
        # make sure that Kernel is present
        print(distro.distro_id+" Monitoring Script..")
        folder_name = distro.repo_link.rsplit('/', 1)[-1]
        if not os.path.exists(cst.PathToClone+folder_name):
            print("[Info] Path to "+folder_name+" does not exists")
            print("[Info] Cloning "+folder_name+" repo")
            # clone single branch
            #git.Git(cst.PathToClone).clone(distro.repo_link)
            git.Repo.clone_from(distro.repo_link,cst.PathToClone+folder_name,branch='master')
            print("[Info] Cloning Complete")

        repo = git.Repo(cst.PathToClone+folder_name)
        print("[Info] Pulling recent changes")
        repo.remotes.origin.pull()
        print("[Info] Git pull complete")
        # get all the tags in the repo
        currDir = os.getcwd()
        os.chdir(cst.PathToClone+folder_name)
        new_kernels = []
        for tag in reversed(repo.tags):
            if tag.name not in kernel_list:
                print("[Info] Found new kernel version "+tag.name+" in distro "+distro.distro_id)
                new_kernels.append(tag.name)
                command = "git checkout "+tag.name
                os.system(command)
                distro.kernel_version = tag.name
                get_logs(folder_name, distro)
        
        return new_kernels

    except Exception:
        print("[Error] Exception occured "+str(Exception))
    finally:
        print("[Info] End of parsing for "+distro.distro_id)

def get_logs(folder_name,distro):
    try:

        #parse maintainers file to get hyperV files
        print("[Info] parsing maintainers files")
        fileList = parseMaintainers(cst.PathToClone+folder_name)
        print("[Info] Received HyperV file paths")
        fileNames = sanitizeFileNames(fileList)

        # Collecting git logs for HyperV files
        print("[Info] Preprocessed HyperV file paths")
        command = "git log --pretty=fuller -p -- "+' '.join(fileNames)+" > "+cst.PathToCommitLog+"/"+folder_name+"Log"
        os.system(command)
        print("[Info] Created HyperV files git logs at "+cst.PathToCommitLog+"/"+folder_name+"Log")

        # Parse git log and dump data into database
        match = DownstreamMatcher(UpstreamPatchTable())
        parse_log(cst.PathToCommitLog+"/"+folder_name+"Log", DistroMatch(), match, distro, distro.distro_id)

    except Exception:
        print("[Error] Exception occured "+str(Exception))
    finally:
        print("[Info] End of parsing for "+distro.distro_id)

if __name__ == '__main__':
    print("Welcome to Patch tracker!!")

    # connect to DB read all entries in Distro table
    Distro_table = DistroTable()
    distro_list = Distro_table.get_distro_list()

    os.makedirs(os.path.dirname(cst.PathToCommitLog), exist_ok=True)

    # for every distro run next
    for distro in distro_list:
        new_kernels = monitor_distro(distro, Distro_table.get_kernel_list(distro.distro_id))
        #insert new Kernels
        Distro_table.insert_kernel_list(new_kernels, distro.distro_id)
        if distro.repo_link.rsplit('/', 1)[-1] == os.path.basename(os.getcwd()):
            print("[Info] resetting git head for repo "+distro.distro_id)
            command = "git clean -dxf"
            os.system(command)
            command = "git reset --hard HEAD"
            os.system(command)
            command = "git checkout master"
            os.system(command)
    
    print("Patch Tracker finishing up")


    
