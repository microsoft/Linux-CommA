# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import logging
import sqlalchemy
from pathlib import Path

import datetime
import git
import pandas
import Util.Config
import Util.Tracking

from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.SqlClasses import PatchData

Util.Config.dry_run = True


# Work in progress to export this data to a particular spreadsheet.
# Currently just comparing an existing spreadsheet and our data.
def export_spreadsheet(spreadsheet="spreadsheet.xlsx"):
    if not Path(spreadsheet).exists():
        logging.error(f"The file {spreadsheet} does not exist")
        return

    xlsx = pandas.ExcelFile(spreadsheet)
    # There’s an empty row after the header.
    df = xlsx.parse(sheet_name="git log", skiprows=[1])
    ss_commits = {c for c in df["Commit ID"]}
    db_commits = {}
    print(f"There are {len(ss_commits)} commits in the spreadsheet")
    with DatabaseDriver.get_session() as s:  # type: sqlalchemy.orm.session.Session
        db_commits = {
            c
            for c, in s.query(PatchData.commitID).filter(
                PatchData.authorTime > datetime.date(2016, 12, 7)
            )
            # Exclude ~1000 CIFS patches.
            .filter(~PatchData.affectedFilenames.like("%fs/cifs%"))
        }
        print(f"There are {len(db_commits)} commits in the database")

    repo = Util.Tracking.get_repo()  # type: git.Repo
    v411 = repo.commit("v4.11")

    def print_commits(missing):
        for sha in missing:
            try:
                commit = repo.commit(sha)
                if not repo.is_ancestor(v411, commit):
                    continue
                filenames = Util.Tracking.get_filenames(commit)
                if any(f.startswith("tools/hv/") for f in filenames):
                    continue
                summary = commit.message.split("\n")[0]
                print(
                    f"{sha}: '{summary[:min(len(summary), 80)]}' by {commit.author.name}"
                )
            except ValueError:
                print(f"{sha}: Missing from repo!")

    print("Commits in spreadsheet missing in database:")
    print_commits(ss_commits - db_commits)

    print("-------------------------------------------")

    print("Commits in database missing in spreadsheet:")
    print_commits(db_commits - ss_commits)
