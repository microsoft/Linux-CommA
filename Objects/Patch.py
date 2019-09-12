
class Patch:
    def __init__(self, subject, author_name, author_email, upstream, description, commit_date, filenames, patch_id = ""):
        self.subject = subject
        self.author_name = author_name
        self.author_email = author_email
        self.upstream = upstream
        self.description = description
        self.commit_date = commit_date
        self.filenames = filenames
        self.patch_id = ""
