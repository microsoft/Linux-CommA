class Diff_code:

    def __init__ (self, diff_filename, diff_add, diff_remove):
        self.diff_filename = diff_filename
        self.diff_add = diff_add
        self.diff_remove = diff_remove
    
    def __str__(self):
        return ""+self.diff_filename+"\n"+self.diff_add+"\n"+self.diff_remove