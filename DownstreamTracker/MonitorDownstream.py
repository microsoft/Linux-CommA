import git
import os
import sys
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# So many noqas due to importing after setting sys.path
import Util.Constants as cst  # noqa E402
from UpstreamTracker.MonitorUpstream import parse_maintainers, sanitize_filenames  # noqa E402
from Objects.UpstreamPatch import UpstreamPatch  # noqa E402
from Objects.DistroPatchMatch import DistroPatchMatch  # noqa E402
from Objects.UbuntuPatch import UbuntuPatch  # noqa E402
from datetime import datetime  # noqa E402
from DatabaseDriver.DistroMatch import DistroMatch  # noqa E402
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable  # noqa E402
from DownstreamTracker.DownstreamMatcher import DownstreamMatcher  # noqa E402
from DatabaseDriver.DistroTable import DistroTable  # noqa E402
from UpstreamTracker.ParseData import process_commits  # noqa E402
from Util.util import list_diff  # noqa E402
from DownstreamTracker.DebianParser import monitor_debian  # noqa E402


def update_kernel_list(repo, distro):
    """
    This updates the stored two latest kernel per distro
    """
    kernel_list = []
    if distro.distro_id.startswith('Ub'):
        # For Ubuntu, we want the latest two tags that are NOT azure-edge
        latest_tags = sorted(repo.tags, key=lambda t: t.commit.committed_date, reverse=True)
        for tag in latest_tags:
            if len(kernel_list) == 2:
                break
            if not tag.name.startswith('Ubuntu-azure-edge'):
                kernel_list.append(tag.name)
    elif distro.distro_id.startswith('SUSE'):
        kernel_list = sorted(repo.git.tag(anything=True).split('\n'))[-2:]
    else:
        kernel_list = sorted(repo.tags, key=lambda t: t.commit.committed_date)[-2:]
    # Update our stored latest two kernel versions if needed
    distro_table = DistroTable()
    old_kernel_list = distro_table.get_kernel_list(distro.distro_id)
    for kernel_version in list_diff(old_kernel_list, kernel_list):
        print("[Info] Deleting old kernel version: %s" % kernel_version)
        distro_table.delete_kernel_version(kernel_version, distro.distro_id)
    for kernel_version in list_diff(kernel_list, old_kernel_list):
        print("[Info] Inserting new kernel version: " + kernel_version)
        distro_table.insert_kernel_version(kernel_version, distro.distro_id)

    return kernel_list


def process_downstream_commits(repo, distro):
    # parse maintainers file to get hyperV files
    print("[Info] parsing maintainers files")
    file_list = parse_maintainers(repo, distro.get_revision())
    print("[Info] Received HyperV file paths")
    file_names = sanitize_filenames(file_list)

    # Handle commits by parsing and matching to upstream
    matcher = DownstreamMatcher(UpstreamPatchTable())
    process_commits(repo, file_names, DistroMatch(), matcher, distro)


def monitor_distro(distro, old_kernel_list):
    # try:
    # make sure that Kernel is present
    print(distro.distro_id+" Monitoring Script..")
    distro_filepath = os.path.join(cst.PATH_TO_REPOS, distro.distro_id)
    # TODO check if repo is here rather than folder?
    if not os.path.exists(distro_filepath):
        print("[Info] Path to %s does not exists" % distro_filepath)
        print("[Info] Cloning %s repo" % distro_filepath)
        # clone repo into folder named distro.distro_id
        git.Git(cst.PATH_TO_REPOS).clone(distro.repo_link, distro.distro_id, "--bare", branch=distro.branch_name)
        repo = git.Repo(distro_filepath)
    else:
        repo = git.Repo(distro_filepath)
        print("[Info] Fetching recent changes")
        repo.git.fetch()

    if distro.distro_id.startswith('Ub'):
        # For Ubuntu, we want to monitor latest two kernel versions
        if (distro.distro_id.startswith('Ub')):
            new_kernels = update_kernel_list(repo, distro)
            for tag in new_kernels:
                print("[Info] Monitoring kernel version %s in distro %s" % (distro.distro_id, tag))
                distro.kernel_version = tag
                process_downstream_commits(repo, distro)
    elif (distro.distro_id.startswith('SUSE')):
        process_downstream_commits(repo, distro)
    else:
        print("[Error] Encountered unsupported distro: %s" % distro.distro_id)
    # except Exception as e:
    #     print("[Error] Exception occured "+str(e))
    # finally:
    #     print("[Info] End of parsing for "+distro.distro_id)


if __name__ == '__main__':
    print("Welcome to Patch tracker!!")

    # connect to DB read all entries in Distro table
    distro_table = DistroTable()
    distro_list = distro_table.get_distro_list()

    # for every distro run next
    for distro in distro_list:
        # For file based repo (debian) we need separate parser
        if distro.distro_id.startswith('Debian'):
            monitor_debian(distro)
        else:
            monitor_distro(distro, distro_table.get_kernel_list(distro.distro_id))

    print("Patch Tracker finished.")
