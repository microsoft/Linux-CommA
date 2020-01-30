import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver

class DistroMatch():
    
    def __init__(self):
        """Initializa database connection"""
        self.cursor = DatabaseDriver.get_instance().cursor
    
    # TODO Set table name in one location rather than these many
    def insertInto(self,DistroPatchMatch, distroId, commitId, date, buglink, kernel_version, author_time):
        """
        Insert data into DistributionPatches-Dev
        """
        conx = self.cursor.execute("insert into [dbo].[DistributionPatches-Dev]\
            ([patchId],[distroId],[commitId],[bugReportLink],[commitTime],[authorMatch],[subjectMatch],[descriptionMatch],[codeMatch],[fileNameMatch],[confidence],[kernelVersion],[authorTime])\
                values(?,?,?,?,?,?,?,?,?,?,?,?,?)",\
                    DistroPatchMatch.upstream_patch_id,distroId,commitId, buglink,date,DistroPatchMatch.author_confidence,DistroPatchMatch.subject_confidence,DistroPatchMatch.description_confidence,0,DistroPatchMatch.filenames_confidence,DistroPatchMatch.confidence,kernel_version, author_time)
        conx.commit()
    
    def check_commit_present(self, commit_id, distro):
        """
        Check if commit is already present in database
        """
        rows = self.cursor.execute("SELECT * from [DistributionPatches-Dev] where commitId like ? and distroId like ? and kernelVersion like ? ;",commit_id,distro.distro_id,distro.kernel_version).fetchall()
        if rows is None or len(rows) == 0:
            return False
        else:
            return True