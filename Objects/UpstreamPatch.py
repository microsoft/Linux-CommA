from Objects.Patch import Patch
from datetime import datetime

class UpstreamPatch(Patch):

    def __init__(self, patch_id, subject, commit_id, author_name, author_email, upstream_date : datetime, description, filenames, diff):
        super().__init__(subject, commit_id, author_name, author_email, upstream_date, description, filenames, diff)
        self.patch_id = patch_id