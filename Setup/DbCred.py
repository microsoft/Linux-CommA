import xml.etree.ElementTree as ET
import Constants.constants as cst
import os
import git


class DatabaseCredentials:
    def __init__(self):
        if os.path.exists(cst.PathToSecret):
            print("[Info] Path to Secrets Repo exists")
            repo = git.Repo(cst.PathToSecret)
            print("[Info] Pulling recent changes")
            repo.remotes.origin.pull()
            print("[Info] Git pull complete")
        else:
            print("[Info] Path to Secrets repo does not exists")
            print("[Info] Cloning Secrets repo")
            git.Git(cst.PathToClone).clone("https://anything:<redacted>@<redacted>")
            print("[Info] Cloning Complete")
        tree = ET.parse(cst.PathToSecret+"/AzureSecretsDevTest.xml")
        root = tree.getroot()
        PT = root.find("PatchTracker")
        self.database_server = PT.find("DatabaseServer").text
        self.database_name = PT.find("DatabaseName").text
        self.database_user = PT.find("DatabaseUser").text
        self.database_password = PT.find("DatabasePassword").text


