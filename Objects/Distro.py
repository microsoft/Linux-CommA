
"""
This represents a downstream distros

"""


# TODO rename to just include upstream... maybe MonitoringSubject to match tb?
class Distro:
    def __init__(self, distro_id, repo_link, commit_link, revision):
        self.distro_id = distro_id
        self.repo_link = repo_link
        self.commit_link = commit_link
        self.revision = revision

