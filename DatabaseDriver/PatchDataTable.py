import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver
import Util.Constants as cst
from Objects.Patch import Patch


class PatchDataTable():

    def __init__(self):
        '''
        Initialize database connection
        '''
        self.cursor = DatabaseDriver.get_instance().cursor

    def check_commit_present(self, commit_id):
        '''
        check if this commit is already present
        '''
        row = self.cursor.execute("SELECT COUNT(*) from [%s] where commitID like ? ;" % cst.UPSTREAM_TABLE_NAME, commit_id).fetchone()
        return row[0] != 0

    def insert_patch(self, patch):
        '''
        dump data into Upstream
        '''
        try:
            conx = self.cursor.execute("insert into [dbo].[" + cst.UPSTREAM_TABLE_NAME + "] \
                ([subject],[commitID],[description],[author],[authorEmail],[authorTime],[commitTime], \
                [affectedFilenames],[commitDiffs],[fixedPatches]) values(?,?,?,?,?,?,?,?,?,?)",
                patch.subject, patch.commit_id, patch.description, patch.author_name, patch.author_email,
                patch.author_time, patch.commit_time, patch.affected_filenames, patch.commit_diffs, patch.fixed_patches)
            conx.commit()
        except pyodbc.Error as Error:
            print("[ERROR] Pyodbc error")
            print(Error)

    def get_commits(self):
        rows = self.cursor.execute("select commitID from [%s] order by commitTime asc" % cst.UPSTREAM_TABLE_NAME).fetchall()

        commits = [row[0] for row in rows]
        return commits

    def save_patch_symbols(self, commit, patch_symbols):
        conx = self.cursor.execute("Update [dbo].[" + cst.UPSTREAM_TABLE_NAME + "] SET [patchSymbols] = ? where commitID = ?", patch_symbols, commit)
        conx.commit()

    def get_patch_symbols(self):
        rows = self.cursor.execute("select patchId,patchSymbols from [" + cst.UPSTREAM_TABLE_NAME + "] where patchSymbols <> ' ' order by commitTime desc").fetchall()

        map = {}
        for r in rows:
            map[r[0]] = r[1].split(" ")

        return map
