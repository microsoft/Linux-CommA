from datetime import datetime

class Patch:
    
    def __init__(self, subject, commit_id, author_name, author_email, upstream_date : datetime, description, filenames, diff):
        self._subject = subject
        self._commit_id = commit_id
        self._author_name = author_name
        self._author_email = author_email
        self._upstream_date = upstream_date
        self._description = description
        self._filenames = filenames
        self._diff = diff

    @classmethod
    def blank(cls):
        return cls("","","","",datetime.now(),"","","")
    
    def __str__(self):
        return " "+self.subject+" "+self.commit_id+" "+str(self.upstream_date)+" "

    @property
    def subject(self):
        """ subject of the patch """
        return self._subject
    
    @subject.setter
    def subject(self, value : str):
        self._subject = value
    
    @property
    def commit_id(self):
        """ commit_id of the patch """
        return self._commit_id
    
    @commit_id.setter
    def commit_id(self, value : str):
        self._commit_id = value
    
    @property
    def author_name(self):
        """ author_name of the patch """
        return self._author_name
    
    @author_name.setter
    def author_name(self, value : str):
        self._author_name = value

    @property
    def author_email(self):
        """ author_email of the patch """
        return self._author_email
    
    @author_email.setter
    def author_email(self, value : str):
        self._author_email = value
    
    @property
    def upstream_date(self):
        """ upstream_date of the patch """
        return self._upstream_date
    
    @upstream_date.setter
    def upstream_date(self, value : datetime):
        self._upstream_date = value

    @property
    def description(self):
        """ description of the patch """
        return self._description
    
    @description.setter
    def description(self, value : str):
        self._description = value

    @property
    def filenames(self):
        """ filenames of the patch """
        return self._filenames
    
    @filenames.setter
    def filenames(self, value : str):
        self._filenames = value
    
    @property
    def diff(self):
        """ diff of the patch """
        return self._diff
    
    @diff.setter
    def diff(self, value : str):
        self._diff = value

