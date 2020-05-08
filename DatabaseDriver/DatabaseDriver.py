import logging
import urllib
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
            logging.info("Using local database")
            engine = create_engine("sqlite:///comma.db", echo=Util.Config.verbose > 2)
        else:
            logging.info("Connecting to database")
            # Get Database credentials
            dbCred = DatabaseCredentials()
            params = urllib.parse.quote_plus(
                "DRIVER={ODBC Driver 17 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s"
                % (
                    dbCred.database_server,
                    dbCred.database_name,
                    dbCred.database_user,
                    dbCred.database_password,
                )
            )
            engine = create_engine(
                "mssql+pyodbc:///?odbc_connect=%s" % params,
                echo=Util.Config.verbose > 2,
            )
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)
        self._Session = sessionmaker(bind=engine)

    @staticmethod
    def get_instance():
        """
        Static access method
        """
        if DatabaseDriver._instance is None:
            DatabaseDriver._instance = DatabaseDriver()
        return DatabaseDriver._instance

    @contextmanager
    def get_session():
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
