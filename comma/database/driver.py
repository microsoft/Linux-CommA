# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import logging
import urllib
from contextlib import contextmanager

import sqlalchemy

from comma.database.credentials import DatabaseCredentials
from comma.database.model import Base
from comma.util import config


# TODO: Rename this class because it conflicts with the module name.
class DatabaseDriver:
    """
    Database driver class for connections
    """

    _instance = None

    def __init__(self):
        """
        Initialize Database connection
        """
        if config.dry_run:
            db_file = "comma.db"
            logging.info(f"Using local SQLite database at '{db_file}'.")
            engine = sqlalchemy.create_engine(f"sqlite:///{db_file}", echo=config.verbose > 2)
        else:
            logging.info("Connecting to remote database...")
            creds = DatabaseCredentials()
            params = urllib.parse.quote_plus(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={creds.server};DATABASE={creds.name};UID={creds.user};PWD={creds.password}"
            )
            engine = sqlalchemy.create_engine(
                f"mssql+pyodbc:///?odbc_connect={params}",
                echo=(config.verbose > 2),
            )
            logging.info("Connected!")
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self.session = sqlalchemy.orm.sessionmaker(bind=engine)

    @classmethod
    def get_instance(cls):
        """
        Static access method
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    @contextmanager
    def get_session(cls) -> sqlalchemy.orm.session.Session:
        instance = cls.get_instance()
        session = instance.session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
