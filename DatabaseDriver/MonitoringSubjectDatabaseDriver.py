from DatabaseDriver.DatabaseDriver import DatabaseDriver
from Objects.MonitoringSubject import MonitoringSubject
import Util.Constants as cst
from Util.util import list_diff


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

    def update_revisions_for_distro(self, distro_id, new_revisions):
        '''
        Updates the database with the given revisions

        new_revisions: list of <revision>s to add under this distro_id
        '''
        current_revisions = self.get_revision_list(distro_id)

        # Remove revisions no longer to be included
        # TODO also remove from missing
        revisions_to_remove = list_diff(current_revisions, new_revisions)
        if (revisions_to_remove):
            print("[Info] For distro: %s, deleting revisions: %s" % (distro_id, revisions_to_remove))
            # This changes a list of A B C to the string ('A','B','C')
            revisions_to_remove_formatted = "('%s')" % "','".join(revisions_to_remove)
            conx = self.cursor.execute("delete from %s where distroID = '%s' and revision in %s"
                % (cst.MONITORING_SUBJECTS_TABLE_NAME, distro_id, revisions_to_remove_formatted))
            conx.commit()

        # Add new revisions
        revisions_to_add = list_diff(new_revisions, current_revisions)
        if (revisions_to_add):
            print("[Info] For distro: %s, adding revisions: %s" % (distro_id, revisions_to_add))
            for revision in revisions_to_add:
                conx = self.cursor.execute("insert into %s ([distroID],[revision]) values(?,?)"
                    % cst.MONITORING_SUBJECTS_TABLE_NAME, distro_id, revision)
                conx.commit()

    def get_revision_list(self, distro_id):
        rows = self.cursor.execute(
            "SELECT revision FROM %s where [distroID] = ?;" % cst.MONITORING_SUBJECTS_TABLE_NAME, distro_id).fetchall()
        return [row[0] for row in rows]
