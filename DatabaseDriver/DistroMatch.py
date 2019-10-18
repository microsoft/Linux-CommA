import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver

class DistroMatch():
    
    def __init__(self):
        """Initializa database connection"""
        self.cursor = DatabaseDriver.get_instance().cursor
    
    def insertInto(self,DistroPatchMatch, distroId, commitId, date, buglink, kernel_version, author_time):
        """
        Insert data into DistributionPatches
        """
        #check if commitId is already present
        rows = self.cursor.execute("SELECT [kernelVersions] from [DistributionPatches] where commitId like ? and distroId like ? ;",commitId,distroId).fetchall()
        if rows is None:
            #get list of kernel_versions
            conx = self.cursor.execute("insert into [dbo].[DistributionPatches]\
                ([patchId],[distroId],[commitId],[bugReportLink],[commitTime],[authorMatch],[subjectMatch],[descriptionMatch],[codeMatch],[fileNameMatch],[confidence],[kernelVersions],[authorTime])\
                    values(?,?,?,?,?,?,?,?,?,?,?,?,?)",\
                        DistroPatchMatch.upstream_patch_id,distroId,commitId, buglink,date,DistroPatchMatch.author_confidence,DistroPatchMatch.subject_confidence,DistroPatchMatch.description_confidence,0,DistroPatchMatch.filenames_confidence,DistroPatchMatch.confidence,kernel_version, author_time)
        else:
            #add exception if row len is greater than 2
            for row in rows:
                new_kernels = row[0] + "," + kernel_version
            conx = self.cursor.execute("Update [dbo].[DistributionPatches]\
                SET kernelVersions = ? where commitId like ? and distroId like ? ;",new_kernels,commitId,distroId)

        conx.commit()
    
    def check_commit_present(self, commit_id, distro):
        """
        Check if commit is already present in database
        """
        #get all commits with same commit_id and distro_id
        rows = self.cursor.execute("SELECT [kernelVersions] from [DistributionPatches] where commitId like ? and distroId like ? ;",commit_id,distro.distro_id).fetchall()
        #check if current kernel_version is present in the rows
        for row in rows:
            if distro.kernel_version in row[0].split(","):
                return True
        return False
