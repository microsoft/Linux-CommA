import logging
import os
import sys
import xml.etree.ElementTree
from pathlib import Path

from git import Repo

import Util.Constants


class DatabaseCredentials:
    def __init__(self):
        secrets_path = Path(Util.Constants.PATH_TO_REPOS, "secrets").resolve()
        if secrets_path.exists():
            repo = Repo(secrets_path)
            logging.info("Pulling recent changes for secrets repo...")
            repo.remotes.origin.pull()
            logging.info("Pull complete.")
        else:
            logging.info("Cloning secrets repo...")
            env_var = "COMMA_SECRETS_URL"
            secrets_url = os.environ.get(env_var)
            if secrets_url is None:
                logging.error(
                    f"Please set the environment variable '{env_var}' as the URL to clone your secrets repo."
                )
                sys.exit(1)
            Repo.clone_from(
                secrets_url, secrets_path,
            )
            logging.info("Cloning complete.")
        tree = xml.etree.ElementTree.parse(
            # TODO: Rename XML file to e.g. `CommASecrets.xml`.
            Path(secrets_path, "PatchTrackerSecrets.xml").resolve()
        )
        root = tree.getroot()
        self.server = root.find("DatabaseServer").text
        self.name = root.find("DatabaseName").text
        self.user = root.find("DatabaseUser").text
        self.password = root.find("DatabasePassword").text
