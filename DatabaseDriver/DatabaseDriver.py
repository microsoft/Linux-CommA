import pyodbc

class DatabaseDriver:

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