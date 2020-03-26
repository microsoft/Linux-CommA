import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver
import Util.Constants as cst
from Objects.Patch import Patch


class PatchDataDriver:
    def __init__(self):
        """
        Initialize database connection
        """
        self.cursor = DatabaseDriver.get_instance().cursor
        self.conx = DatabaseDriver.get_instance().connection

    def check_commit_present(self, commit_id):
        """
        check if this commit is already present
        """
        row = self.cursor.execute(
            "SELECT COUNT(*) from [%s] where commitID like ? ;"
            % cst.UPSTREAM_TABLE_NAME,
            (commit_id,),
        ).fetchone()
        return row[0] != 0

    def insert_patch(self, patch):
        """
        dump data into Upstream
        """
        try:
            self.cursor.execute(
                "insert into ["
                + cst.UPSTREAM_TABLE_NAME
                + "] \
                ([subject],[commitID],[description],[author],[authorEmail],[authorTime],[commitTime], \
                [affectedFilenames],[commitDiffs],[fixedPatches]) values(?,?,?,?,?,?,?,?,?,?)",
                (
                    patch.subject,
                    patch.commit_id,
                    patch.description,
                    patch.author_name,
                    patch.author_email,
                    patch.author_time,
                    patch.commit_time,
                    patch.affected_filenames,
                    patch.commit_diffs,
                    patch.fixed_patches,
                ),
            )
            self.conx.commit()
        except pyodbc.Error as Error:
            print("[ERROR] Pyodbc error")
            print(Error)

    def get_commits(self):
        rows = self.cursor.execute(
            "select commitID from [%s] order by commitTime asc"
            % cst.UPSTREAM_TABLE_NAME
        ).fetchall()
        return [row[0] for row in rows]

    def save_patch_symbols(self, commit, patch_symbols):
        self.cursor.execute(
            "Update ["
            + cst.UPSTREAM_TABLE_NAME
            + "] SET [patchSymbols] = ? where commitID = ?",
            (patch_symbols, commit),
        )
        self.conx.commit()

    def get_patch_symbols(self):
        rows = self.cursor.execute(
            "select patchId,patchSymbols from ["
            + cst.UPSTREAM_TABLE_NAME
            + "] where patchSymbols <> ' ' order by commitTime desc"
        ).fetchall()

        map = {}
        for r in rows:
            map[r[0]] = r[1].split(" ")

        return map
