import pyodbc
from Setup.DbCred import DatabaseCredentials as DbCred


class DatabaseDriver:
    """
    Database driver class for connections
    """
    _instance = None

    def __init__(self):
        """
        Initialize Database connection
        """
        print("Connecting to Database...")
        # Get Database credentials
        dbCred = DbCred()
        self.connection = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s'
                    % (dbCred.database_server, dbCred.database_name, dbCred.database_user, dbCred.database_password))
        self.cursor = self.connection.cursor()

    @staticmethod
    def get_instance():
        """
        Static access method
        """
        if DatabaseDriver._instance is None:
            DatabaseDriver._instance = DatabaseDriver()
        return DatabaseDriver._instance

    def __del__(self):
        self.connection.close()
