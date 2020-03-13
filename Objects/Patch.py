from datetime import datetime


class Patch:
    def __init__(
        self,
        subject,
        commit_id,
        description,
        author_name,
        author_email,
        author_time: datetime,
        commit_time: datetime,
        affected_filenames,
        commit_diffs,
        fixed_patches="",
    ):
        self.subject = subject
        self.commit_id = commit_id
        self.description = description
        self.author_name = author_name
        self.author_email = author_email
        self.author_time = author_time
        self.commit_time = commit_time
        self.affected_filenames = affected_filenames
        self.commit_diffs = commit_diffs
        self.fixed_patches = fixed_patches

    @classmethod
    def blank(cls):
        return cls("", "", "", "", "", datetime.now(), datetime.now(), "", "")
