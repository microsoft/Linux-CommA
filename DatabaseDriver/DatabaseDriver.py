import pyodbc

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
        self.server = 'linuxpatchtracker.database.windows.net'
        self.database = 'linuxpatchtracker'
        self.username = 'lsgadmin'
        self.password = input("Enter database password")
        self.connection = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+self.server+';DATABASE='+self.database+';UID='+self.username+';PWD='+ self.password)
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