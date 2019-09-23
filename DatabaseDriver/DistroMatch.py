import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver

class DistroMatch():
    
    def __init__(self):
        """Initializa database connection"""
        self.cursor = DatabaseDriver.get_instance().cursor
    
    def insertInto(self,DistroPatchMatch, distroId, commitId, date, buglink):
        """
        Insert data into upstream_patchtracker
        """
        conx = self.cursor.execute("insert into [dbo].[DistributionPatches]\
            ([patchId],[distroId],[commitId],[bugReportLink],[datetimeAdded],[authorMatch],[subjectMatch],[descriptionMatch],[codeMatch],[fileNameMatch],[confidence])\
                values(?,?,?,?,?,?,?,?,?,?,?)",\
                    DistroPatchMatch.upstream_patch_id,distroId,commitId, buglink,date,DistroPatchMatch.author_confidence,DistroPatchMatch.subject_confidence,DistroPatchMatch.description_confidence,0,DistroPatchMatch.filenames_confidence,DistroPatchMatch.confidence)
        conx.commit()
    
    def check_commit_present(self, commit_id):
        """
        Check if commit is already present in database
        """
        rows = self.cursor.execute("SELECT * from [DistributionPatches] where commitId like ?;",commit_id).fetchall()
        if rows is None or len(rows) == 0:
            return False
        else:
            return True