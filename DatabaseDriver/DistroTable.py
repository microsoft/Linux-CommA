import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from Objects.Distro import Distro

class DistroMatch():
    
    def __init__(self):
        """Initializa database connection"""
        self.cursor = DatabaseDriver.get_instance().cursor
    
    def insertInto(self,distro_object):
        """
        Insert data into distro
        """
        conx = self.cursor.execute("INSERT INTO [dbo].[Distro] ([distroId],[repoLink],[Kernel Version],[commitLink]) VALUES (?,?,?,?)",\
                    distro_object.distro_id,distro_object.repo_link,distro_object.kernel_version,distro_object.commit_link)
        conx.commit()
    
    def checkIfPresent(self, distro_id):
        """
        Check if distro is already present in database
        """
        rows = self.cursor.execute("SELECT * from [Distro] where distroId like ?;",distro_id).fetchall()
        if rows is None or len(rows) == 0:
            return False
        else:
            return True
    
    def get_distro_list(self):
        rows = self.cursor.execute("SELECT [distroId], [repoLink], [Kernel Version], [commitLink] FROM [dbo].[Distro];").fetchall()
        distros = []
        for r in rows:
            distros.append(Distro(r[0],r[1],r[2],r[3]))
        
        return distros
    