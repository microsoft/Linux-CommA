import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from Objects.UpstreamPatch import UpstreamPatch
import Constants.constants as cst


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
        rows = self.cursor.execute("SELECT * from [" + cst.UPSTREAM_TABLE_NAME + "] where commitId like ? ;", commit_id).fetchall()
        if rows is None or len(rows) == 0:
            return False
        else:
            return True

    def insert_upstream(self, commit_id, author_name, author_id, commit_sub, commit_msg, diff_files, commit_time, diff_fNames, author_time, fixed_patches):
        '''
        dump data into Upstream
        '''
        try:
            conx = self.cursor.execute("insert into [dbo].[" + cst.UPSTREAM_TABLE_NAME + "]([patchName],[state],[commitId],[commitMessage],[author],[authorEmail],[patchFiles],[commitTime],[diff_fileNames],[authorTime],[fixedPatches]) values(?,?,?,?,?,?,?,?,?,?,?)",
                commit_sub, "Upstream", commit_id, commit_msg, author_name, author_id, diff_files, commit_time, diff_fNames, author_time, fixed_patches)
            conx.commit()
        except pyodbc.Error as Error:
            print("[ERROR] Pyodbc error")
            print(Error)

    def get_upstream_patch(self):
        rows = self.cursor.execute("select [patchId],[patchName],[state],[commitId],[author],[authorEmail],[commitTime],[commitMessage],[diff_fileNames],[patchFiles],[authorTime],[fixedPatches] from [" + cst.UPSTREAM_TABLE_NAME + "];").fetchall()

        upstream_patch_list = [UpstreamPatch(r[0], r[1], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11]) for r in rows]
        return upstream_patch_list

    def get_patch_diff(self):
        rows = self.cursor.execute("SELECT patchId, patchFiles  from [" + cst.UPSTREAM_TABLE_NAME + "];").fetchall()
        map = {}
        for r in rows:
            print("Print: "+str(r[0])+"--"+r[1]) 
            map[r[0]]=r[1]

        return map

    def get_commits(self):
        rows = self.cursor.execute("select commitid from [" + cst.UPSTREAM_TABLE_NAME + "] order by commitTime asc").fetchall()

        commits = []
        for r in rows:
            commits.append(r[0])
        return commits

    def save_patch_symbols(self, commit, patch_symbols):
        conx = self.cursor.execute("Update [dbo].[" + cst.UPSTREAM_TABLE_NAME + "] SET [patchSymbols] = ? where commitId = ?", patch_symbols, commit)
        conx.commit()

    def get_patch_symbols(self):
        rows = self.cursor.execute("select patchId,patchSymbols from [" + cst.UPSTREAM_TABLE_NAME + "] where patchSymbols <> ' ' order by commitTime desc").fetchall()

        map = {}
        for r in rows:
            map[r[0]] = r[1].split(" ")

        return map
