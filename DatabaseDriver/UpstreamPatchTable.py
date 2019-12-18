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
    
    def check_commit_present(self, commit_id, distro):
        '''
        check if this commit is already present in Upstream
        '''
        rows = self.cursor.execute("SELECT * from [Upstream-Dev] where commitId like ? ;",commit_id).fetchall()
        if rows is None or len(rows) == 0:
            return False
        else:
            return True
    
    def insert_Upstream(self, commit_id,author_name,author_id,commit_sub,commit_msg,diff_files,commit_time,diff_fNames,author_time):
        '''
        dump data into Upstream 
        '''
        try:
            conx = self.cursor.execute("insert into [dbo].[Upstream-Dev]([patchName],[state],[commitId],[commitMessage],[author],[authorEmail],[patchFiles],[commitTime],[diff_fileNames],[authorTime]) values(?,?,?,?,?,?,?,?,?,?)",commit_sub,"Upstream",commit_id, commit_msg, author_name,author_id,diff_files,commit_time,diff_fNames,author_time)
            conx.commit()
        except pyodbc.Error as Error:
            print("[ERROR] Pyodbc error")
            print(Error)

    def get_upstream_patch(self):
        rows = self.cursor.execute("select [patchId],[patchName],[state],[commitId],[author],[authorEmail],[commitTime],[commitMessage],[diff_fileNames],[patchFiles],[authorTime] from [Upstream-PatchTracker];").fetchall()
        
        upstream_patch_list = [UpstreamPatch(r[0],r[1],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10]) for r in rows]
        return upstream_patch_list
    
    