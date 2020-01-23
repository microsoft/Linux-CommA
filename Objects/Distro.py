
"""
This represents a downstream distros

"""


class Distro:
    def __init__(self, distro_id, repo_link, kernel_version, commit_link, branch_name):
        self.distro_id = distro_id
        self.repo_link = repo_link
        self.kernel_version = kernel_version
        self.commit_link = commit_link
        self.branch_name = branch_name