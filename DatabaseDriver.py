import pyodbc


class DatabaseDriver:
    server = ''
    database = ''
    username = ''
    password = ''
    connection = ''
    cursor = ''
    def __init__(self):
        print("Connecting to Database...")
        self.server = 'linuxpatchtracker.database.windows.net'
        self.database = 'linuxpatchtracker'
        self.username = 'lsgadmin'
        self.password = input("Enter database password")
        self.connection = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+self.server+';DATABASE='+self.database+';UID='+self.username+';PWD='+ self.password)
        self.cursor = self.connection.cursor()

    def executeSelect(self):
        rows = self.cursor.execute("select * from [Upstream-PatchTracker];").fetchall()
        for r in rows:
            print(r)
    
    def insertData(self):
        '''
        Insert data into Upstream-PatchTracker
        '''
        conx = self.cursor.execute("insert into [dbo].[Upstream-PatchTracker]([patchName],[state],[commitId],[commitMessage],[author],[authorEmail],[patchFiles]) values(?,?,?,?,?,?,?)","TESTPATCH3","complete","fakeID", "This is a dummy msg","AM","fakemail@dummy.org","file")
        conx.commit()
    
    def checkCommitPresent(self, commit_id):
        '''
        check if this commit is already present in Upstream
        '''
        return False
    