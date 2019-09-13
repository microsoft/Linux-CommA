import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from Objects.UpstreamPatch import UpstreamPatch
from datetime import datetime

class UpstreamPatchTable():

    def __init__(self):
        '''
        Initialize database connection
        '''
        self.cursor = DatabaseDriver.get_instance().cursor

    def execute_select(self):
        '''
        View all the data from Upstream-PatchTracker
        '''
        rows = self.cursor.execute("select [patchId],[patchName],[state],[commitId],[commitMessage],[author],[authorEmail] ,[commitTimestamp],[patchFiles],[commitTime],[diff_fileNames] from [Upstream-PatchTracker];").fetchall()
        for r in rows:
            print(r)
    
    def insert_data_test(self):
        '''
        Insert data into Upstream-PatchTracker
        '''
        conx = self.cursor.execute("insert into [dbo].[Upstream-PatchTracker]([patchName],[state],[commitId],[commitMessage],[author],[authorEmail],[commitTime],[patchFiles]) values(?,?,?,?,?,?,?,?)","TESTPATCH3","complete","fakeID", "This is a dummy msg","AM","fakemail@dummy.org","2019-05-07 13:33:31","file")
        conx.commit()
    
    def check_commit_present(self, commit_id):
        '''
        check if this commit is already present in Upstream
        '''
        rows = self.cursor.execute("SELECT * from [Upstream-PatchTracker] where commitId like ?;",commit_id).fetchall()
        if rows is None or len(rows) == 0:
            return False
        else:
            return True
    
    def insert_Upstream(self, commit_id,author_name,author_id,commit_sub,commit_msg,diff_files,datetime_obj,diff_fNames):
        '''
        dump data into Upstream 
        '''
        try:
            conx = self.cursor.execute("insert into [dbo].[Upstream-PatchTracker]([patchName],[state],[commitId],[commitMessage],[author],[authorEmail],[patchFiles],[commitTime],[diff_fileNames]) values(?,?,?,?,?,?,?,?,?)",commit_sub,"Upstream",commit_id, commit_msg, author_name,author_id,diff_files,datetime_obj,diff_fNames)
            conx.commit()
        except pyodbc.Error as Error:
            print("[ERROR] Pyodbc error")
            print(Error)

    def get_upstream_patch(self):
        rows = self.cursor.execute("select [patchId],[patchName],[state],[commitId],[author],[authorEmail],[commitTime],[commitMessage],[diff_fileNames],[patchFiles] from [Upstream-PatchTracker];").fetchall()
        upstream_patch_list = []
        for r in rows:
            upstream_patch_list.append(UpstreamPatch(r[0],r[1],r[3],r[4],r[5],r[6],r[7],r[8],r[9]))
        
        return upstream_patch_list
    
    