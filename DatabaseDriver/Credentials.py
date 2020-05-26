import logging
import os
import pathlib
import sys
import xml.etree.ElementTree

import Util.Tracking


class DatabaseCredentials:
    def __init__(self):
        path = Util.Tracking.get_repo_path("secrets")

        env_var = "COMMA_SECRETS_URL"
        secrets_url = os.environ.get(env_var)
        if not path.exists() and secrets_url is None:
            logging.error(
                f"Please set the environment variable '{env_var}' as the URL to clone your secrets repo."
            )
            sys.exit(1)

        # NOTE: It is possible that `secrets_url` might be `None`, but
        # at this point we're assuming it's already cloned and
        # therefore just needs to be pulled. Also, it is possible the
        # _server_ from which we're cloning does not support
        # `--shallow-since`, so we have to disable this here.
        Util.Tracking.get_repo(
            name="secrets", url=secrets_url, bare=False, shallow=False, pull=True
        )

        root = xml.etree.ElementTree.parse(
            # TODO: Rename XML file to e.g. `CommASecrets.xml`.
            pathlib.Path(path, "PatchTrackerSecrets.xml").resolve()
        ).getroot()

        self.server = root.find("DatabaseServer").text
        self.name = root.find("DatabaseName").text
        self.user = root.find("DatabaseUser").text
        self.password = root.find("DatabasePassword").text
