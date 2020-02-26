import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver
import Util.Constants as cst
from Objects.Patch import Patch


class PatchDataDriver():

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

    def get_patches_from_commit_ids(self, commit_ids):
        '''
        Translates a list of commit_ids into a list of (patch id, patch)
        '''
        # This changes a list of A B C to ('A', 'B', 'C')
        commit_ids_formatted = "('%s')" % "', '".join(commit_ids)
        rows = self.cursor.execute("select [subject],[commitID],[description],[author],[authorEmail],[authorTime],[commitTime], \
                [affectedFilenames],[commitDiffs],[fixedPatches],[patchID] from [%s] where commitID in %s"
            % (cst.UPSTREAM_TABLE_NAME, commit_ids_formatted)).fetchall()
        return [(row[10], Patch(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9])) for row in rows]

    def get_commits(self):
        rows = self.cursor.execute("select commitID from [%s] order by commitTime asc" % cst.UPSTREAM_TABLE_NAME).fetchall()
        return [row[0] for row in rows]

    def save_patch_symbols(self, commit, patch_symbols):
        conx = self.cursor.execute("Update [dbo].[" + cst.UPSTREAM_TABLE_NAME + "] SET [patchSymbols] = ? where commitID = ?", patch_symbols, commit)
        conx.commit()

    def get_patch_symbols(self):
        rows = self.cursor.execute("select patchId,patchSymbols from [" + cst.UPSTREAM_TABLE_NAME + "] where patchSymbols <> ' ' order by commitTime desc").fetchall()

        map = {}
        for r in rows:
            map[r[0]] = r[1].split(" ")

        return map
