import git
import os
import sys
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# So many noqas due to importing after setting sys.path
import Util.Constants as cst
from UpstreamTracker.MonitorUpstream import get_hyperv_filenames
from DatabaseDriver.PatchDataTable import PatchDataTable
from DatabaseDriver.MonitoringSubjectDatabaseDriver import MonitoringSubjectDatabaseDriver
from DatabaseDriver.MissingPatchesDatabaseDriver import MissingPatchesDatabaseDriver
from Util.util import list_diff
# from DownstreamTracker.DebianParser import monitor_debian


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
    monitoring_subject_table = MonitoringSubjectDatabaseDriver()
    old_kernel_list = monitoring_subject_table.get_kernel_list(distro.distro_id)
    for kernel_version in list_diff(old_kernel_list, kernel_list):
        print("[Info] Deleting old kernel version: %s" % kernel_version)
        monitoring_subject_table.delete_kernel_version(kernel_version, distro.distro_id)
    for kernel_version in list_diff(kernel_list, old_kernel_list):
        print("[Info] Inserting new kernel version: " + kernel_version)
        monitoring_subject_table.insert_kernel_version(kernel_version, distro.distro_id)

    return kernel_list


def monitor_subject(monitoring_subject, repo):
    """
    Update the missing patches in the database for this monitoring_subject

    monitoring_subject: The MonitoringSubject we are updating
    repo: The git repo object pointing to relevant upstream linux repo
    """

    filenames = get_hyperv_filenames(repo, monitoring_subject.revision)

    missing_commit_ids = repo.git.log('--no-merges', '--right-only', '--cherry-pick', '--pretty=format:%H',
        '%s...master' % monitoring_subject.revision, '--', filenames).split("\n")

    # Update database to reflect latest missing patches
    # First, we translate the commitIDs we have into patchIDs, then we update downstream database
    patch_data_db_driver = PatchDataTable()
    missing_patch_ids = patch_data_db_driver.get_patch_ids_from_commit_ids(missing_commit_ids)

    missing_patches_db_driver = MissingPatchesDatabaseDriver()
    missing_patches_db_driver.update_missing_patches(monitoring_subject.monitoring_subject_id, missing_patch_ids)


if __name__ == '__main__':
    print("Welcome to Patch tracker!!")

    # connect to DB read all entries in Distro table
    monitoring_subject_db_driver = MonitoringSubjectDatabaseDriver()
    monitoring_subjects = monitoring_subject_db_driver.get_monitoring_subjects()
    repo_links = monitoring_subject_db_driver.get_repo_links()

    # This should always be present
    path_to_linux = os.path.join(cst.PATH_TO_REPOS, cst.LINUX_REPO_NAME)
    repo = git.Repo(path_to_linux)

    # Add repos as a remote origin if not already added
    unique_distros = list(set([subject.distro_id for subject in monitoring_subjects]))
    current_remotes = repo.git.remote()
    for distro_id in unique_distros:
        if (distro_id not in current_remotes and not distro_id.startswith("Debian")):  # Debian we handle in a different way
            print("[Info] Adding remote origin for %s from %s" % (distro_id, repo_links[distro_id]))
            repo.create_remote(distro_id, url=repo_links[distro_id])

    # TODO Update ubuntu (more?) revisions

    repo.git.fetch('--all')

    for monitoring_subject in monitoring_subjects:
        if monitoring_subject.distro_id.startswith('Debian'):
            # TODO don't skip debian
            print('skipping debian')
        else:
            print("[Info] Monitoring Script starting for Distro: %s, revision: %s.."
                    % (monitoring_subject.distro_id, monitoring_subject.revision))
            monitor_subject(monitoring_subject, repo)

    print("Patch Tracker finished.")
