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

def sort_kernel_list(tags, distro):
    kernel_list = []
    if distro.distro_id.startswith('Ub'):
        latest_tags = sorted(tags, key=lambda t: t.commit.committed_date, reverse=True)
        for tag in latest_tags:
            if len(kernel_list) == 2:
                break
            if not tag.name.startswith('Ubuntu-azure-edge'):
                kernel_list.append(tag.name)
    else:
        kernel_list = sorted(tags, key=lambda t: t.commit.committed_date)[-2:]
    # if old_kenrel_list contains diff elements than this one 
    # then there is new latest kernel
    # delete entries of old latest kernel 
    distro_table = DistroTable()
    old_kernel_list = distro_table.get_kernel_list(distro.distro_id)
    for old_kernel in old_kernel_list:
        if old_kernel not in kernel_list:
            print("[Info] Found kernel version no longer latest kernel: "+old_kernel)
            distro_table.delete_kernel_version(old_kernel,distro.distro_id)
    
    return kernel_list
    

def monitor_distro(distro, old_kernel_list):
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
        new_kernels = sort_kernel_list(repo.tags, distro)
        for tag in new_kernels :
            if tag not in old_kernel_list:
                print("[Info] Found new kernel version "+tag+" in distro "+distro.distro_id)
                command = "git checkout "+tag
                os.system(command)
                distro.kernel_version = tag
                get_logs(folder_name, distro)
        
        return new_kernels

    except Exception as e:
        print("[Error] Exception occured "+str(e))
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
        command = "git log --pretty=fuller -p -- "+' '.join(fileNames)+" "+cst.RedirectOp+" "+cst.PathToCommitLog+"/"+folder_name+"Log"
        os.system(command)
        print("[Info] Created HyperV files git logs at "+cst.PathToCommitLog+"/"+folder_name+"Log")

        # Parse git log and dump data into database
        match = DownstreamMatcher(UpstreamPatchTable())
        parse_log(cst.PathToCommitLog+"/"+folder_name+"Log", DistroMatch(), match, distro, distro.distro_id)

    except Exception as e:
        print("[Error] Exception occured "+str(e))
        print("[Info]Git rebase to master ")
        command = "git clean -dxf"
        os.system(command)
        command = "git checkout master"
        os.system(command)
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


    
