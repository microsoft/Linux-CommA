class Diff_code:

    def __init__ (self, diff_filename, diff_add, diff_remove):
        self.diff_filename = diff_filename
        self.diff_add = diff_add
        self.diff_remove = diff_remove
    
    def __str__(self):
        return "filename|:"+self.diff_filename+"\n add+"+self.diff_add+"\n remove-"+self.diff_remove

    def is_empty(self):
        if (self.diff_filename is None or len(self.diff_filename) == 0) and \
        (self.diff_add is None or len(self.diff_add) == 0) and \
        (self.diff_remove is None or len(self.diff_remove) == 0):
            return True
        return False