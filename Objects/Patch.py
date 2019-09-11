
class Patch:
    def __init__(self, subject, author_name, author_email, upstream, description, commit_date, filenames, patch_id = ""):
        self.subject = subject
        self.commit_id = commit_id
        self.author_name = author_name
        self.author_email = email
        self.upstream = upstream
        self.description = description
        self.commit_date = commit_date
        self.filenames = filesnames
        self.patch_id = ""
