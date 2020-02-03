from Objects.Patch import Patch
from datetime import datetime


class UpstreamPatch(Patch):

    def __init__(self, patch_id, subject, commit_id, author_name, author_email, commit_time: datetime, description, filenames, diff, author_time  datetime, fixed_patches):
        super().__init__(subject, commit_id, author_name, author_email, commit_time, description, filenames, diff, author_time)
        self.patch_id = patch_id
        self.fixed_patches = fixed_patches