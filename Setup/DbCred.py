import xml.etree.ElementTree as ET
import Constants.constants as cst
import os
import git


class DatabaseCredentials:
    def __init__(self):
        if os.path.exists(cst.PathToSecret):
            print("[Info] Path to Secrets Repo exists")
            repo = git.Repo(cst.PathToSecret)
            print("[Info] Pulling recent changes for secrets repo")
            repo.remotes.origin.pull()
            print("[Info] Git pull complete")
        else:
            print("[Info] Path to Secrets repo does not exists")
            print("[Info] Cloning Secrets repo")
            git.Git(cst.PathToClone).clone("https://anything:<redacted>@<redacted>")
            print("[Info] Cloning Complete")
        tree = ET.parse(cst.PathToSecret+"/PatchTrackerSecrets.xml")
        root = tree.getroot()
        self.database_server = root.find("DatabaseServer").text
        self.database_name = root.find("DatabaseName").text
        self.database_user = root.find("DatabaseUser").text
        self.database_password = root.find("DatabasePassword").text


