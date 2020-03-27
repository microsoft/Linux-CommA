import urllib
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import DatabaseDriver.SqlClasses as Orm
import Util.Config
from Setup.DbCred import DatabaseCredentials as DbCred


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
            # Populate distros locally
            if Util.Config.dry_run:
                add_distros()
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

    def __del__(self):
        self.connection.close()


def add_distros():
    distros = [
        Orm.Distros(
            distroID="Debian9-backport",
            repoLink="https://salsa.debian.org/kernel-team/linux.git",
        ),
        Orm.Distros(distroID="SUSE12", repoLink="https://github.com/openSUSE/kernel",),
        Orm.Distros(
            distroID="Ubuntu16.04",
            repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/xenial",
        ),
        Orm.Distros(
            distroID="Ubuntu18.04",
            repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/bionic",
        ),
        Orm.Distros(
            distroID="Ubuntu19.04",
            repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/disco",
        ),
        Orm.Distros(
            distroID="Ubuntu19.10",
            repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/eoan",
        ),
    ]
    with DatabaseDriver.get_session() as s:
        if s.query(Orm.Distros).first() is None:
            s.add_all(distros)
