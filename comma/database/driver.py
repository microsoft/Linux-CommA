# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Provide a class for managing database connections and sessions
"""


import logging
import os
import urllib
from contextlib import contextmanager

import sqlalchemy

from comma.database.model import Base, Distros, MonitoringSubjects
from comma.exceptions import CommaDatabaseError, CommaDataError


LOGGER = logging.getLogger(__name__)


class DatabaseDriver:
    """
    Database driver managing connections
    """

    def __init__(self, dry_run, echo=False):
        # Enable INFO-level logging when program is logging debug
        # It's not ideal, because the messages are INFO level, but only enabled with debug

        if dry_run:
            db_file = "comma.db"
            LOGGER.info("Using local SQLite database at '%s'.", db_file)
            engine = sqlalchemy.create_engine(f"sqlite:///{db_file}", echo=echo)
        else:
            LOGGER.info("Connecting to remote database...")
            engine = sqlalchemy.create_engine(self._get_mssql_conn_str(), echo=echo)

        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self.session_factory = sqlalchemy.orm.sessionmaker(bind=engine)

    @staticmethod
    def _get_mssql_conn_str() -> sqlalchemy.engine.Engine:
        """
        Create a connection string for MS SQL server and create engine instance
        """

        # Verify credentials are available
        for envvar in ("COMMA_DB_URL", "COMMA_DB_NAME", "COMMA_DB_USERNAME", "COMMA_DB_PW"):
            if not os.environ.get(envvar):
                raise CommaDatabaseError(f"{envvar} is not defined in the current environment")

        params = urllib.parse.quote_plus(
            ";".join(
                (
                    "DRIVER={ODBC Driver 17 for SQL Server}",
                    f"SERVER={os.environ['COMMA_DB_URL']}",
                    f"DATABASE={os.environ['COMMA_DB_NAME']}",
                    f"UID={os.environ['COMMA_DB_USERNAME']}",
                    f"PWD={os.environ['COMMA_DB_PW']}",
                )
            )
        )

        return f"mssql+pyodbc:///?odbc_connect={params}"

    @contextmanager
    def get_session(self) -> sqlalchemy.orm.session.Session:
        """
        Context manager for getting a database session
        """

        session = self.session_factory()

        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_revisions_for_distro(self, distro_id, revs):
        """
        Updates the database with the given revisions

        new_revisions: list of <revision>s to add under this distro_id
        """
        with self.get_session() as session:
            revs_to_delete = (
                session.query(MonitoringSubjects)
                .filter_by(distroID=distro_id)
                .filter(~MonitoringSubjects.revision.in_(revs))
            )
            for subject in revs_to_delete:
                LOGGER.info("For distro %s, deleting revision: %s", distro_id, subject.revision)

            # This is a bulk delete and we close the session immediately after.
            revs_to_delete.delete(synchronize_session=False)

        with self.get_session() as session:
            for rev in revs:
                # Only add if it doesn't already exist. We're dealing
                # with revisions on the scale of 1, so the number of
                # queries and inserts here doesn't matter.
                if (
                    session.query(MonitoringSubjects)
                    .filter_by(distroID=distro_id, revision=rev)
                    .first()
                    is None
                ):
                    LOGGER.info("For distro %s, adding revision: %s", distro_id, rev)
                    session.add(MonitoringSubjects(distroID=distro_id, revision=rev))

    def iter_downstream_targets(
        self,
    ):
        """List downstream targets"""

        with self.get_session() as session:
            yield from session.query(Distros.distroID, MonitoringSubjects.revision).outerjoin(
                MonitoringSubjects, Distros.distroID == MonitoringSubjects.distroID
            ).all()

    def add_downstream_target(self, name, url, revision):
        """
        Add a downstream target
        """

        with self.get_session() as session:
            # See if remote exists
            if existing := session.query(Distros).filter_by(distroID=name).one_or_none():
                # If URL is different, overwrite with warning
                if url and existing.repoLink != url:
                    LOGGER.warning(
                        "Overwriting existing remote %s URL: %s", name, existing.repoLink
                    )
                    existing.repoLink = url

                else:
                    LOGGER.info(
                        "Using existing remote %s at %s", existing.distroID, existing.repoLink
                    )

            # If new remote, create
            elif url:
                session.add(Distros(distroID=name, repoLink=url))
                LOGGER.info("Successfully added new repo %s at %s", name, url)

            # If no URL was given, error
            else:
                raise CommaDataError(f"Repository '{name}' given without URL not found in database")

            # See if target exists
            if (
                existing := session.query(MonitoringSubjects.distroID)
                .filter_by(distroID=name)
                .filter_by(revision=revision)
                .one_or_none()
            ):
                LOGGER.info(
                    "Target already exists for revision '%s' in distro '%s'", revision, name
                )

            # If new target, create
            else:
                session.add(MonitoringSubjects(distroID=name, revision=revision))
                LOGGER.info(
                    "Successfully added target for revision '%s' in distro '%s'", revision, name
                )

    def delete_repo(self, name):
        """
        Deletes a repo and all associated monitoring subjects
        """

        with self.get_session() as session:
            targets = session.query(MonitoringSubjects).filter_by(distroID=name)
            for target in targets:
                LOGGER.info(
                    "Deleting downstream target: remote=%s revision=%s", name, target.revision
                )
            targets.delete(synchronize_session=False)

            LOGGER.info("Deleting remote: %s", name)
            session.query(Distros).filter_by(distroID=name).delete(synchronize_session=False)

    def delete_downstream_target(self, name, revision):
        """
        Remove a downstream target
        """

        with self.get_session() as session:
            LOGGER.info("Deleting downstream target: remote=%s revision=%s", name, revision)
            session.query(MonitoringSubjects).filter_by(distroID=name).filter_by(
                revision=revision
            ).delete(synchronize_session=False)

    def get_downstream_repos(self):
        """
        Get the repos used in downstream targets
        """

        with self.get_session() as session:
            return tuple(
                repo for (repo,) in session.query(MonitoringSubjects.distroID).distinct().all()
            )
