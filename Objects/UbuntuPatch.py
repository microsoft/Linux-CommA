from Objects.Patch import Patch
from datetime import datetime

class Ubuntu_Patch(Patch):

    def __init__(self, patch_id, subject, commit_id, author_name, author_email, upstream_date : datetime, description, filenames, diff, buglink):
        super().__init__(subject, commit_id, author_name, author_email, upstream_date, description, filenames, diff)
        self.buglink = buglink
    