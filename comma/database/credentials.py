# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os


class DatabaseCredentials:
    def __init__(self):
        self.server = os.environ.get("COMMA_DB_URL")
        self.name = os.environ.get("COMMA_DB_NAME")
        self.user = os.environ.get("COMMA_DB_USERNAME")
        self.password = os.environ.get("COMMA_DB_PW")
        assert all([self.server, self.name, self.user, self.password]), (
            "Missing a credential environment variable. Check that "
            "COMMA_DB_URL, COMMA_DB_NAME, COMMA_DB_USERNAME and COMMA_DB_PW "
            "are all set with the correct database info."
        )
