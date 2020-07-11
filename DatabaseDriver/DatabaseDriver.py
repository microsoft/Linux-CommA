# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import logging
import urllib
from contextlib import contextmanager

import sqlalchemy

import Util.Config
from DatabaseDriver.Credentials import DatabaseCredentials
from DatabaseDriver.SqlClasses import Base


# TODO: Rename this class because it conflicts with the module name.
class DatabaseDriver:
    """
    Database driver class for connections
    """

    _instance = None
    _Session = None

    def __init__(self):
        """
        Initialize Database connection
        """
        if Util.Config.dry_run:
            db_file = "comma.db"
            logging.info(f"Using local SQLite database at '{db_file}'.")
            engine = sqlalchemy.create_engine(
                f"sqlite:///{db_file}", echo=(Util.Config.verbose > 2)
            )
        else:
            logging.info("Connecting to remote database...")
            creds = DatabaseCredentials()
            params = urllib.parse.quote_plus(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={creds.server};DATABASE={creds.name};UID={creds.user};PWD={creds.password}"
            )
            engine = sqlalchemy.create_engine(
                f"mssql+pyodbc:///?odbc_connect={params}",
                echo=(Util.Config.verbose > 2),
            )
            logging.info("Connected!")
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._Session = sqlalchemy.orm.sessionmaker(bind=engine)

    @staticmethod
    def get_instance():
        """
        Static access method
        """
        if DatabaseDriver._instance is None:
            DatabaseDriver._instance = DatabaseDriver()
        return DatabaseDriver._instance

    @contextmanager
    def get_session() -> sqlalchemy.orm.session.Session:
        instance = DatabaseDriver.get_instance()
        session = instance._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
