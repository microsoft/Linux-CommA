from DatabaseDriver.DatabaseDriver import DatabaseDriver
import Util.Constants as cst
from Util.util import list_diff


class MissingPatchesDatabaseDriver():

    def __init__(self):
        """Initializa database connection"""
        self.cursor = DatabaseDriver.get_instance().cursor

    def update_missing_patches(self, monitoring_subject_id, missing_patches):
        """
        This updates the database to reflect the current missing patches of this monitoring subject.

        missing_patches: A list of missing patchIDs
        """
        # First, get old missing patch_ids in database
        rows = self.cursor.execute("SELECT patchID from [%s] where monitoringSubjectID like ?;"
            % cst.DOWNSTREAM_TABLE_NAME, monitoring_subject_id).fetchall()
        old_missing_patch_ids = [row[0] for row in rows]

        # Remove patches that now are NOT missing
        patches_to_remove = list_diff(old_missing_patch_ids, missing_patches)
        if (patches_to_remove):
            # This changes a list of A B C to the string (A, B, C)
            patches_to_remove_formatted = "(%s)" % ", ".join(str(patch_id) for patch_id in patches_to_remove)
            conx = self.cursor.execute("delete from %s where patchID in %s"
                % (cst.DOWNSTREAM_TABLE_NAME, patches_to_remove_formatted))
            conx.commit()

        # Add patches which are newly missing
        new_missing_patch_ids = list_diff(missing_patches, old_missing_patch_ids)
        if (new_missing_patch_ids):
            for patch_id_to_add in new_missing_patch_ids:
                conx = self.cursor.execute("insert into %s ([monitoringSubjectID],[patchID]) values(?,?)"
                    % cst.DOWNSTREAM_TABLE_NAME, monitoring_subject_id, patch_id_to_add)
                conx.commit()
