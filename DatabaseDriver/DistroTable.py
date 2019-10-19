import pyodbc
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from Objects.Distro import Distro

class DistroTable():
    
    def __init__(self):
        """Initializa database connection"""
        self.cursor = DatabaseDriver.get_instance().cursor
    
    def insertInto(self,distro_object):
        """
        Insert data into distro
        """
        conx = self.cursor.execute("INSERT INTO [dbo].[Distro] ([distroId],[repoLink],[commitLink]) VALUES (?,?,?,?)",\
                    distro_object.distro_id,distro_object.repo_link,distro_object.commit_link)
        conx.commit()
    
    def check_commit_present(self, distro_id):
        """
        Check if distro is already present in database
        """
        rows = self.cursor.execute("SELECT * from [Distro] where distroId like ?;",distro_id).fetchall()
        if rows is None or len(rows) == 0:
            return False
        else:
            return True
    
    def get_distro_list(self):
        rows = self.cursor.execute("SELECT [distroId], [repoLink], [commitLink] FROM [dbo].[Distro];").fetchall()
        distros = []
        for r in rows:
            distros.append(Distro(r[0],r[1],'',r[2]))
        
        return distros

    def get_kernel_list(self, distro_id):
        rows = self.cursor.execute("SELECT [kernelVersion] FROM [dbo].[Distro_kernel] where [distroId] = ?;",distro_id).fetchall()
        kernel_versions = []
        for r in rows:
            kernel_versions.append(r[0])
        
        return kernel_versions

    def insert_kernel_list(self, kernel_list, distro_id):
        if kernel_list is None or len(kernel_list) == 0:
            return
        for kernel_version in kernel_list:
            conx = self.cursor.execute("INSERT INTO [dbo].[Distro_kernel] ([distroId],[kernelVersion]) VALUES (?,?)", distro_id,kernel_version)
            conx.commit()
    
    def delete_kernel_version(self, kernel_version, distro_id):
        rows = self.cursor.execute('delete from [dbo].[Distro_kernel] where [distroId] = ? and [kernelVersion] = ?',distro_id,kernel_version)
        print("[Info] Deleted "+rows.rowcount+" rows")
        rows.commit()

    