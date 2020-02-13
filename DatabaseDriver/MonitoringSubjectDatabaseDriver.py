from DatabaseDriver.DatabaseDriver import DatabaseDriver
from Objects.MonitoringSubject import MonitoringSubject
import Util.Constants as cst


class MonitoringSubjectDatabaseDriver():

    def __init__(self):
        """Initialize database connection"""
        self.cursor = DatabaseDriver.get_instance().cursor

    def get_monitoring_subjects(self):
        rows = self.cursor.execute("SELECT [monitoringSubjectID], [distroID], [revision] FROM %s;"
            % cst.MONITORING_SUBJECTS_TABLE_NAME).fetchall()
        monitoring_subjects = []
        for r in rows:
            monitoring_subjects.append(MonitoringSubject(r[0], r[1], r[2]))

        return monitoring_subjects

    def get_repo_links(self):
        '''
        returns a dict mapping a distro_id to repo_link
        '''
        rows = self.cursor.execute("SELECT [distroID], [repoLink] FROM %s;"
            % cst.DISTROS_TABLE_NAME).fetchall()
        repo_links = {}
        for row in rows:
            repo_links[row[0]] = row[1]

        return repo_links

    def get_kernel_list(self, distro_id):
        rows = self.cursor.execute("SELECT [kernelVersion] FROM [dbo].[Distro_kernel] where [distroId] = ?;", distro_id).fetchall()
        kernel_versions = []
        for r in rows:
            kernel_versions.append(r[0])

        return kernel_versions

    def insert_kernel_version(self, kernel_version, distro_id):
        if kernel_version is None:
            return
        conx = self.cursor.execute("INSERT INTO [dbo].[Distro_kernel] ([distroId],[kernelVersion]) VALUES (?,?)",
                                   distro_id, kernel_version)
        conx.commit()

    def delete_kernel_version(self, kernel_version, distro_id):
        rows = self.cursor.execute('delete from [dbo].[Distro_kernel] where [distroId] = ? and [kernelVersion] = ?',
                                   distro_id, kernel_version)
        print("[Info] Deleted "+str(rows.rowcount)+" rows")
        rows.commit()
