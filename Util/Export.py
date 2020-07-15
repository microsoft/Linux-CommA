# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import logging
import re
import sqlalchemy
from datetime import datetime
from pathlib import Path

import git
import openpyxl
import Util.Config
import Util.Tracking

from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.SqlClasses import PatchData

Util.Config.dry_run = True

# Work in progress to export this data to a particular spreadsheet.
# Currently just comparing an existing spreadsheet and our data.
def export_spreadsheet(in_file="spreadsheet.xlsx", out_file="export.xlsx"):
    if not Path(in_file).exists():
        logging.error(f"The file {in_file} does not exist")
        return

    # There’s an empty row after the header, so skip the header and
    # all ‘None’ values. The sheet is manually named “git log”.
    wb = openpyxl.load_workbook(filename=in_file)
    ws = wb["git log"]
    wb_commits = {c.value for c in ws["A"][1:] if c.value is not None}

    db_commits = set()
    with DatabaseDriver.get_session() as s:  # type: sqlalchemy.orm.session.Session
        db_commits = {
            c
            for c, in s.query(PatchData.commitID).filter(
                # Exclude ~1000 CIFS patches.
                ~PatchData.affectedFilenames.like("%fs/cifs%")
            )
        }

    repo = Util.Tracking.get_repo()  # type: git.Repo
    base_commit = repo.commit("v4.11")

    def include_commit(sha):
        try:
            commit = repo.commit(sha)
            # Skip commits before the chosen base.
            if not repo.is_ancestor(base_commit, commit):
                return False
            # Skip commits to tools.
            filenames = Util.Tracking.get_filenames(commit)
            if any(f.startswith("tools/hv/") for f in filenames):
                return False
            return True
        except ValueError:
            return False

    def commit_to_row(sha):
        commit = repo.commit(sha)
        date = datetime.utcfromtimestamp(commit.authored_date).strftime("%Y-%m-%d")
        summary = commit.message.split("\n")[0]
        # Get the ‘v5.7’ from ‘v5.7-rc1-2-gc81992e7f’
        tag = repo.git.describe(sha, contains=None)
        release = re.search(r"(v[^-~]*)[-~]", tag).group(1)
        return {
            "A": sha,
            "B": date,
            "C": release,
            "G": summary[: min(len(summary), 120)],
        }

    commits = [
        commit_to_row(sha)
        for sha in list(db_commits - wb_commits)
        if include_commit(sha)
    ]

    for row in commits:
        ws.append(row)
    print(f"Exported {len(commits)} commits to {out_file}!")

    # Save spreadsheet.
    wb.save(out_file)
