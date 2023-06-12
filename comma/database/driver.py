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

from comma.database.model import Base
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
