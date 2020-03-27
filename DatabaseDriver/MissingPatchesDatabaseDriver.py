import Util.Constants as cst
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from Util.util import list_diff


class MissingPatchesDatabaseDriver:
    def __init__(self):
        """Initializa database connection"""
        self.cursor = DatabaseDriver.get_instance().cursor
        self.conx = DatabaseDriver.get_instance().connection

    def update_missing_patches(self, monitoring_subject_id, missing_patches):
        """
        This updates the database to reflect the current missing patches of this monitoring subject.

        missing_patches: A list of missing patchIDs
        """
        # First, get old missing patch_ids in database
        rows = self.cursor.execute(
            "SELECT patchID from [%s] where monitoringSubjectID like ?;"
            % cst.DOWNSTREAM_TABLE_NAME,
            (monitoring_subject_id,),
        ).fetchall()
        old_missing_patch_ids = [row[0] for row in rows]

        # Remove patches that now are NOT missing
        patches_to_remove = list_diff(old_missing_patch_ids, missing_patches)
        print(
            "[Info] Removing %s patches from DB that are no longer missing."
            % len(patches_to_remove)
        )
        if patches_to_remove:
            # This changes a list of A B C to the string (A, B, C)
            patches_to_remove_formatted = "(%s)" % ", ".join(
                str(patch_id) for patch_id in patches_to_remove
            )
            self.cursor.execute(
                "delete from %s where patchID in %s"
                % (cst.DOWNSTREAM_TABLE_NAME, patches_to_remove_formatted)
            )
            self.conx.commit()

        # Add patches which are newly missing
        new_missing_patch_ids = list_diff(missing_patches, old_missing_patch_ids)
        print(
            "[Info] Adding %s patches to DB that are now missing."
            % len(new_missing_patch_ids)
        )
        if new_missing_patch_ids:
            for patch_id_to_add in new_missing_patch_ids:
                self.cursor.execute(
                    "insert into %s ([monitoringSubjectID],[patchID]) values(?,?)"
                    % cst.DOWNSTREAM_TABLE_NAME,
                    (monitoring_subject_id, patch_id_to_add),
                )
                self.conx.commit()

    def remove_missing_patches_for_subject(self, monitoring_subject_id):
        """
        Removes all data related to the given subject
        """
        self.cursor.execute(
            "delete from %s where monitoringSubjectID = '%d'"
            % (cst.DOWNSTREAM_TABLE_NAME, monitoring_subject_id)
        )
        self.conx.commit()
