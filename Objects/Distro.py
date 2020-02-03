
"""
This represents a downstream distros

"""


class Distro:
    def __init__(self, distro_id, repo_link, commit_link, branch_name, kernel_version):
        self.distro_id = distro_id
        self.repo_link = repo_link
        self.commit_link = commit_link
        self.branch_name = branch_name
        self.kernel_version = kernel_version

    def get_revision(self):
        # TODO sort out branch vs kernel... maybe just have revision?
        if (self.kernel_version != ""):
            return self.kernel_version
        return self.branch_name
