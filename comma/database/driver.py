# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Provide a class for managing database connections and sessions
"""


import logging
import os
import sys
import urllib
from contextlib import contextmanager

import sqlalchemy

from comma.database.model import Base, MonitoringSubjects
from comma.util import config


LOGGER = logging.getLogger(__name__)


class DatabaseDriver:
    """
    Database driver managing connections
    """

    _instance = None

    def __init__(self):
        if config.dry_run:
            db_file = "comma.db"
            LOGGER.info("Using local SQLite database at '%s'.", db_file)
            engine = sqlalchemy.create_engine(f"sqlite:///{db_file}", echo=config.verbose > 2)
        else:
            LOGGER.info("Connecting to remote database...")
            engine = self._get_mssql_engine()
            LOGGER.info("Connected!")

        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self.session = sqlalchemy.orm.sessionmaker(bind=engine)

    @staticmethod
    def _get_mssql_engine() -> sqlalchemy.engine.Engine:
        """
        Create a connection string for MS SQL server and create engine instance
        """

        # Verify credentials are available
        for envvar in ("COMMA_DB_URL", "COMMA_DB_NAME", "COMMA_DB_USERNAME", "COMMA_DB_PW"):
            if not os.environ.get(envvar):
                sys.exit(f"{envvar} is not defined in the current environment")

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

        return sqlalchemy.create_engine(
            f"mssql+pyodbc:///?odbc_connect={params}",
            echo=(config.verbose > 2),
        )

    @classmethod
    @contextmanager
    def get_session(cls) -> sqlalchemy.orm.session.Session:
        """
        Context manager for getting a database session
        """

        # Only support a single instance
        if cls._instance is None:
            cls._instance = cls()
        session = cls._instance.session()

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
