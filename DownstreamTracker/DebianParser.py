from datetime import datetime
import os,sys,inspect
# currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
# parentdir = os.path.dirname(currentdir)
# sys.path.insert(0,parentdir) 
import Util.Constants as cst
from UpstreamTracker.ParseData import get_patch_object, insert_patch
from DatabaseDriver.DistroMatch import DistroMatch
from UpstreamTracker.MonitorUpstream import parse_maintainers, sanitize_filenames
from Util.util import contains_filepath
# from DownstreamTracker.MonitorDownstream import *
import git
import re
from DownstreamTracker.DownstreamMatcher import DownstreamMatcher
from DatabaseDriver.PatchDataDriver import PatchDataDriver


def check_hyperV_patch(patch_filenames, filenames):

    for file in patch_filenames:
        for hV_file in filenames:
            if contains_filepath(file, hV_file):
                return True

    return False


def get_hv_filenames(kernel_version):
    '''
    Parse maintainers upstream with same kernel version to get Maintainers file
    '''
    path_to_linux = os.path.join(cst.PATH_TO_REPOS, "linux-stable")
    if os.path.exists(path_to_linux):
        print("[Info] Path to Linux Repo exists")
        repo = git.Repo(path_to_linux)
        print("[Info] Fetching recent changes")
        repo.git.fetch()
    else:
        print("[Info] Path to Linux repo does not exists. Cloning linux repo.")
        git.Git(cst.PATH_TO_REPOS).clone("git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git", "linux-stable", "--bare")
        repo = git.Repo(path_to_linux)
    print("[Info] parsing maintainers files")
    fileList = parse_maintainers(repo, 'v'+kernel_version)
    print("[Info] Received HyperV file paths")
    return sanitize_filenames(fileList)


def parse_file_log(filename, db, match, distro, hv_filenames):
    '''
    parse_file_log will scrape each patch from git log
    '''
    patch = get_patch_object("Debian")
    diff_started = False
    commit_msg_started = False
    diff_filenames = []
    count_added = 0
    count_present = 0
    try:
        with open(filename, 'r', encoding="utf8") as f:
            try:
                for line in f:
                    words = line.strip().split()
                    if words is None or len(words) == 0:
                        continue
                    if len(words) >= 3 and words[0] == "From:":

                        if len(patch.subject) > 0 and not db.check_commit_present(patch.subject, distro):
                            # check if commit already present
                            patch.filenames = " ".join(diff_filenames)
                            if check_hyperV_patch(diff_filenames, hv_filenames):
                                print(" HyperV patch:"+patch.subject)
                                # if true then match upstream and insert
                                insert_patch(db, match, distro, patch, distro.distro_id)
                                count_added += 1
                            # print("New commit "+patch.subject)

                            patch = get_patch_object("debian")
                            diff_started = False
                            commit_msg_started = False
                            diff_filenames = []

                        for word in range(1, len(words)-1):
                            patch.author_name += " "+words[word]
                        patch.author_email = words[len(words)-1]
                        patch.author_name = patch.author_name.strip()

                    elif words[0] == "Subject:":
                        patch.subject = ' '.join(words[1:])
                        commit_msg_started = True
                    elif len(words) == 7 and words[0] == "Date:":
                        date = ""
                        for i in range(1, len(words)-1):
                            date += " "+words[i]
                        date = date.strip()
                        try:
                            patch.author_time = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S')
                        except ValueError:
                            patch.author_time = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
                        commit_msg_started = True
                    elif words[0] == 'Bug-Debian:':
                        patch.buglink = words[1]
                    elif words[0] == "Forwarded:":
                        continue
                    elif commit_msg_started and line.startswith('--- a/'):
                        fileN = words[1][2:]
                        diff_filenames.append(fileN)
                        commit_msg_started = False
                        diff_started = True
                        patch.diff += fileN
                    elif commit_msg_started:
                        ignore_phrases = ('reported-by:', 'signed-off-by:', 'reviewed-by:', 'acked-by:', 'cc:')
                        lowercase_line = line.strip().lower()
                        if lowercase_line.startswith(ignore_phrases):
                            continue
                        else:
                            patch.description += line.strip()
                    elif diff_started and line.startswith('--- a/'):
                        fileN = words[1][2:]
                        diff_filenames.append(fileN)
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
            patch.filenames = " ".join(diff_filenames)
            if check_hyperV_patch(diff_filenames, hv_filenames):
                print(" ************hyperV related patch*********************" + patch.subject)
                # if true then match upstream
                insert_patch(db, match, distro, patch, distro.distro_id)
                count_added += 1

    except IOError:
        print("[Error] Failed to read " + filename)
    finally:
        print("[Info] Added new commits: " + str(count_added)+"\t skipped patches:" + str(count_present))
        f.closed


def get_kernel_version(folder_name):
    '''
    get_kernel_version returns kernel version of debian based repo.
    '''
    changelog_content = open(folder_name+"/debian/changelog", 'r').read()
    kernel_version = re.search(r'[\d]+.[\d]+.[\d]+', changelog_content).group()
    return kernel_version


def get_base_kernel_patches(distro):
    '''
    Get missing patches from upstream in kernel stable version
    '''
    pass


def monitor_debian(distro):
    print(distro.distro_id+" Monitoring Script..")
    distro_filepath = os.path.join(cst.PATH_TO_REPOS, distro.distro_id)
    # TODO check if repo is here rather than folder?
    if not os.path.exists(distro_filepath):
        print("[Info] Path to %s does not exists" % distro_filepath)
        print("[Info] Cloning %s repo" % distro_filepath)
        # clone repo into folder named distro.distro_id
        git.Git(cst.PATH_TO_REPOS).clone(distro.repo_link, distro.distro_id, branch=distro.branch_name)
        repo = git.Repo(distro_filepath)
    else:
        repo = git.Repo(distro_filepath)
        print("[Info] Fetching recent changes")
        repo.git.checkout(distro.branch_name)
        repo.git.pull()
    # Get kernel Base Version
    distro.kernel_version = get_kernel_version(distro_filepath)
    hv_filenames = get_hv_filenames(distro.kernel_version)
    get_base_kernel_patches(distro)
    currDir = os.getcwd()
    find_path = cst.PATH_TO_REPOS+"/"+distro.distro_id+"/debian/patches"
    command = "find " + find_path + " -name '*.patch' -exec cat " + cst.RedirectOp \
        + currDir + "/" + cst.PATH_TO_REPOS + "/" + distro.distro_id + ".log"+" {} \;"
    os.system(command)
    parse_file_log(cst.PATH_TO_REPOS + "/" + distro.distro_id+".log", DistroMatch(), "", distro, hv_filenames)
