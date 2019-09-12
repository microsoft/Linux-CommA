import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver

class UpstreamPatch(DatabaseDriver):

    def __init__(self):
        '''
        Initialize database connection
        '''
        super.__init__()

    def executeSelect(self):
        '''
        View all the data from Upstream-PatchTracker
        '''
        rows = self.cursor.execute("select [patchId],[patchName],[state],[commitId],[commitMessage],[author],[authorEmail] ,[commitTimestamp],[patchFiles],[commitTime],[diff_fileNames] from [Upstream-PatchTracker];").fetchall()
        for r in rows:
            print(r)
    
    def insertDataTest(self):
        '''
        Insert data into Upstream-PatchTracker
        '''
        conx = self.cursor.execute("insert into [dbo].[Upstream-PatchTracker]([patchName],[state],[commitId],[commitMessage],[author],[authorEmail],[commitTime],[patchFiles]) values(?,?,?,?,?,?,?,?)","TESTPATCH3","complete","fakeID", "This is a dummy msg","AM","fakemail@dummy.org","2019-05-07 13:33:31","file")
        conx.commit()
    
    def checkCommitPresent(self, commit_id):
        '''
        check if this commit is already present in Upstream
        '''
        rows = self.cursor.execute("SELECT * from [Upstream-PatchTracker] where commitId like ?;",commit_id).fetchall()
        if rows is None or len(rows) == 0:
            return False
        else:
            return True
    
    def insertIntoUpstream(self, commit_id,author_name,author_id,commit_sub,commit_msg,diff_files,datetime_obj,diff_fNames):
        '''
        dump data into Upstream 
        '''
        try:
            conx = self.cursor.execute("insert into [dbo].[Upstream-PatchTracker]([patchName],[state],[commitId],[commitMessage],[author],[authorEmail],[patchFiles],[commitTime],[diff_fileNames]) values(?,?,?,?,?,?,?,?,?)",commit_sub,"Upstream",commit_id, commit_msg, author_name,author_id,diff_files,datetime_obj,diff_fNames)
            conx.commit()
        except pyodbc.Error as Error:
            print("[ERROR] Pyodbc error")
            print(Error)
    
    def __del__(self):
        self.connection.close()
    