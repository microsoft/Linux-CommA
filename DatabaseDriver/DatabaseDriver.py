import urllib
import DatabaseDriver.SqlClasses as Orm
import Util.Config
from contextlib import contextmanager
from Setup.DbCred import DatabaseCredentials as DbCred
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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
            print("[Info] Using local database...")
            engine = create_engine("sqlite:///comma.db", echo=True)
        else:
            print("[Info] Connecting to database...")
            # Get Database credentials
            dbCred = DbCred()
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
                "mssql+pyodbc:///?odbc_connect=%s" % params, echo=True
            )
        # TODO: Actually use the ORM. This is to prove the database
        # interface works.
        Orm.Base.metadata.bind = engine
        Orm.Base.metadata.create_all(engine)
        self._Session = sessionmaker(bind=engine)
        # TODO: Remove these when raw database calls are no longer
        # being made.
        self.connection = engine.raw_connection()
        self.cursor = self.connection.cursor()

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
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def __del__(self):
        self.connection.close()
