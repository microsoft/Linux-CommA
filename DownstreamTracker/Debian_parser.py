from datetime import datetime
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from UpstreamTracker.ParseData import get_patch_object, insert_patch
from DatabaseDriver.DistroMatch import DistroMatch
from UpstreamTracker.MonitorChanges import parseMaintainers,sanitizeFileNames
from Objects.Distro import Distro
from Util.util import contains_filepath
from DownstreamTracker.MonitorUbuntu import *

filenames = []


def check_hyperV_patch(patch_filenames):
    global filenames
    if len(filenames) == 0:
        print("[Info] parsing maintainers files")
        fileList = parseMaintainers(cst.PathToClone+'linux-stable')
        print("[Info] Received HyperV file paths")
        filenames = sanitizeFileNames(fileList)

    for file in patch_filenames:
        for hV_file in filenames:
            if contains_filepath(file, hV_file):
                return True
    
    return False



def parse_file_log( filename, db, match, distro, indicator):
    '''
    parse_file_log will scrape each patch from git log
    '''
    patch = get_patch_object("Debian")
    diff_started=False
    commit_msg_started=False
    diff_fileNames = []
    count_added = 0
    count_present = 0
    skip_commit = False
    try:
        with open (filename, 'r', encoding="utf8") as f:
            try:    
                for line in f:
                    words = line.strip().split()
                    if words == None or len(words)==0:
                        continue
                    if len(words) >= 3 and words[0] == "From:":
                        
                        if len(patch.subject) > 0 and not db.check_commit_present(patch.subject, distro):
                            #check if commit already present
                            patch.filenames = " ".join(diff_fileNames)
                            if check_hyperV_patch(diff_fileNames):
                                print(" ************hyperV related patch*********************"+patch.subject)
                                #if true then match upstream
                                insert_patch(db,match,distro,patch,distro.distro_id)
                            print("New commit "+patch.subject)

                            patch = get_patch_object("debian")
                            diff_started=False
                            commit_msg_started=False
                            skip_commit = False
                            diff_fileNames = []

                        for word in range(1,len(words)-1):
                            patch.author_name += " "+words[word]
                        patch.author_email = words[len(words)-1]
                        patch.author_name = patch.author_name.strip()
                        
                    elif words[0] == "Subject:":
                        patch.subject=' '.join(words[1:])
                        commit_msg_started=True
                    elif len(words) == 7 and words[0] == "Date:":
                        date=""
                        for i in range(1,len(words)-1):
                            date += " "+words[i]
                        date = date.strip()
                        try:
                            patch.author_time = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S')
                        except ValueError:
                            patch.author_time = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
                        commit_msg_started=True
                    elif words[0] == 'Bug-Debian:':
                        patch.buglink = words[1]
                    elif words[0] == "Forwarded:":
                        continue
                    elif commit_msg_started and line.startswith('--- a/'):
                        fileN = words[1][1:]
                        diff_fileNames.append(fileN)
                        commit_msg_started = False
                        diff_started=True
                        patch.diff += fileN
                    elif commit_msg_started:
                        ignore_phrases = ('reported-by:', 'signed-off-by:', 'reviewed-by:', 'acked-by:', 'cc:')
                        lowercase_line = line.strip().lower()
                        if lowercase_line.startswith(ignore_phrases):
                            continue
                        else:
                            patch.description += line.strip()
                    elif diff_started and line.startswith('--- a/'):
                        fileN = words[1][1:]
                        diff_fileNames.append(fileN)
                    elif diff_started:
                        if line.startswith('+') or line.startswith('-'):
                            patch.diff += "\n"+line.strip()
                    else:
                        print("[Warning] No parsing done for the following line..")
                        print(line)
                        
            except Exception as e:
                print("[Error] "+str(e))
                print(line)

        if (patch.subject is not None or len(patch.subject) != 0) and not db.check_commit_present(patch.subject, distro):
            patch.filenames = " ".join(diff_fileNames)
            print(patch)
            insert_patch(db,match,distro,patch,distro.distro_id)
            count_added += 1
            
    except IOError:
        print("[Error] Failed to read "+ filename)
    finally:
        print("[Info] Added new commits: "+str(count_added)+"\t skipped patches:"+str(count_present))
        f.closed

def get_kernel_version(folder_name):
    # parse changelog to get kernel version
    return "4.9.88"

def parse_upstream_kernel(distro,folder_name):
    if os.path.exists(cst.PathToClone+"/linux-stable"):
        print("[Info] Path to Linux Repo exists")
        repo = git.Repo(cst.PathToClone+"/linux-stable")
        print("[Info] Pulling recent changes")
        #repo.remotes.origin.pull()
        print("[Info] Git pull complete")
    else:
        print("[Info] Path to Linux repo does not exists")
        print("[Info] Cloning linux repo")
        git.Git(cst.PathToClone).clone("git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git")
        print("[Info] Cloning Complete")

    currDir = os.getcwd()
    os.chdir(cst.PathToClone+"/linux-stable")

    print("[Info] resetting kernel version to "+distro.kernel_version)
    # git rebase to kernel version
    command = "git checkout tags/v"+distro.kernel_version
    #os.system(command)

    print("[Info] parsing maintainers files")
    fileList = parseMaintainers(cst.PathToClone+"/linux-stable")
    print("[Info] Received HyperV file paths")
    fileNames = sanitizeFileNames(fileList)
    print("[Info] Preprocessed HyperV file paths")

    
    command = "git log --pretty=fuller -p -- "+' '.join(fileNames)+" "+cst.RedirectOp+" "+cst.PathToCommitLog+"/"+distro.kernel_version+".log"
    os.system(command)
    print("[Info] Created HyperV git logs at "+cst.PathToCommitLog)

    # Parse git log and dump data into database
    match = DownstreamMatcher(UpstreamPatchTable())
    parse_log(cst.PathToCommitLog+"/"+distro.kernel_version+".log", DistroMatch(), match, distro, distro.distro_id)

def monitor_debian(folder_name, distro):
    # Get kernel Base Version
    distro.kernel_version = get_kernel_version(folder_name)
    # parse upstream and store result as debian in downstream
    #parse_upstream_kernel(distro,cst.PathToLinux)
    # parse debain repo
    os.chdir(cst.PathToClone+"/"+folder_name+"/debian/patches")

    command = "find . -name '*.patch' -exec cat "+cst.RedirectOp+cst.PathToCommitLog+"/"+folder_name+".log"+" {} \;"
    os.system(command)
    parse_file_log(cst.PathToCommitLog+"/"+folder_name+".log",DistroMatch(),"",distro,"Debain")


if __name__ == '__main__':
    print("Starting patch scraping from files..")
    distro = Distro("Debian9-backport","https://salsa.debian.org/kernel-team/linux.git","","","stretch-backports")
    monitor_distro(distro,"")
    #parse_file_log(cst.PathToCommitLog+"/debian.log",DistroMatch(),"",distro,"Debain")