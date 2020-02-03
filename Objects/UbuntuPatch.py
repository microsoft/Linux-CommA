from Objects.Patch import Patch
from datetime import datetime

class UbuntuPatch(Patch):

    def __init__(self, subject, commit_id, author_name, author_email, commit_time : datetime, description, filenames, diff, buglink, author_time : datetime):
        super().__init__(subject, commit_id, author_name, author_email, commit_time, description, filenames, diff, author_time)
        self.buglink = buglink
    