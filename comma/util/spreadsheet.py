# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions for exporting data to Excel spreadsheets
"""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import git
import openpyxl
import sqlalchemy
from openpyxl.cell.cell import Cell
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from comma.database.model import Distros, MonitoringSubjects, PatchData
from comma.util.tracking import get_filenames


LOGGER = logging.getLogger(__name__)


def get_column(worksheet: Worksheet, name: str) -> Cell:
    """Gets the header cell for the given column name.

    The column names are the values of the cells in the first row,
    e.g. 'Commit Title'. Use 'cell.column' for the numeric column, or
    'cell.column_letter' for the letter. Given a row, index into it
    with 'row[get_column(ws, "Commit Title").column]'.

    """
    LOGGER.debug("Looking for column with name '%s'...", name)
    return next(cell for cell in worksheet[1] if cell.value == name)


def get_cell(worksheet, name: str, row) -> Cell:
    """Get the cell of the named column in this commit's row."""
    return worksheet[f"{get_column(worksheet, name).column_letter}{row}"]


def get_workbook(in_file: str) -> Tuple[Workbook, Worksheet]:
    """Open the spreadsheet and return it and the 'git log' worksheet.

    Also fix the pivot table so the spreadsheet doesn't crash.

    """
    if not Path(in_file).exists():
        LOGGER.error("The file %s does not exist", in_file)
        sys.exit(1)
    workbook = openpyxl.load_workbook(filename=in_file)

    # Force refresh of pivot table in “Pivot” worksheet.
    LOGGER.debug("Finding worksheet named 'Pivot'...")
    pivot = workbook["Pivot"]._pivots[0]  # pylint: disable=protected-access
    pivot.cache.refreshOnLoad = True

    # The worksheet is manually named “git log”.
    LOGGER.debug("Finding worksheet named 'git log'...")
    worksheet = workbook["git log"]

    return (workbook, worksheet)


class Spreadsheet:
    """
    Parent object for symbol operations
    """

    def __init__(self, config, database, repo) -> None:
        self.config = config
        self.database = database
        self.repo = repo

    def get_db_commits(self) -> Dict[str, int]:
        """Query the 'PatchData' table for all commit hashes and IDs."""
        with self.database.get_session() as session:  # type: sqlalchemy.orm.session.Session
            return dict(
                session.query(PatchData.commitID, PatchData.patchID).filter(
                    # Exclude ~1000 CIFS patches.
                    ~PatchData.affectedFilenames.like("%fs/cifs%")
                )
            )

    def include_commit(self, sha: str, base_commit: git.Commit) -> bool:
        """Determine if we should export the commit."""
        # Skip empty values (such as if ‘cell.value’ was passed).
        if sha is None:
            LOGGER.warning("Given SHA was 'None'!")
            return False
        # Skip commits that are not in the repo.
        try:
            commit = self.repo.commit(sha)
        except ValueError:
            LOGGER.warning("Commit '%s' not in repo!", sha)
            return False
        # Skip commits before the chosen base.
        if base_commit and not self.repo.is_ancestor(base_commit, commit):
            LOGGER.debug("Commit '%s' is too old!", sha)
            return False
        # Skip commits to tools.
        filenames = get_filenames(commit)
        if any(f.startswith("tools/hv/") for f in filenames):
            LOGGER.debug("Commit '%s' is in 'tools/hv/'!", sha)
            return False
        return True

    def get_release(self, sha: str) -> str:
        """Get the ‘v5.7’ from ‘v5.7-rc1-2-gc81992e7f’."""
        try:
            # NOTE: This must be ordered “--contains <SHA>” for Git.
            tag = self.repo.git.describe("--contains", sha)
            # Use "(v[^-~]+(-rc[0-9]+)?)[-~]" to include ‘-rcX’  # pylint: disable=wrong-spelling-in-comment
            return re.search(r"(v[^-~]*)[-~]", tag)[1]
        except git.GitCommandError:
            return "N/A"

    def create_commit_row(self, sha: str, worksheet: Worksheet) -> Dict[str, Any]:
        """Create a row with the commit's SHA, date, release and title."""
        commit = self.repo.commit(sha)
        # TODO (Issue 40): Some (but not all) of this info is available in the
        # database, so if add the release to the database we can skip
        # using the commit here.
        date = datetime.utcfromtimestamp(commit.authored_date).date()
        title = commit.message.split("\n")[0]

        # The worksheet has additional columns with manually entered
        # info, which we can’t insert, so we skip them.
        def get_letter(name: str) -> str:
            return get_column(worksheet, name).column_letter

        return {
            get_letter("Commit ID"): sha,
            get_letter("Date"): date,
            get_letter("Release"): self.get_release(sha),
            get_letter("Commit Title"): title[: min(len(title), 120)],
        }

    def export_commits(self, in_file: str, out_file: str) -> None:
        """This adds commits from the database to the spreadsheet.

        This lets us automatically update the spreadsheet by adding commits which CommA found.
        It adds the basic information available from the commit.

        """
        workbook, worksheet = get_workbook(in_file)
        column = get_column(worksheet, "Commit ID").column_letter
        wb_commits = {cell.value for cell in worksheet[column][1:] if cell.value is not None}

        # Collect the commits in the database and not in the workbook, but that we want to include.
        db_commits = self.get_db_commits()
        tag = "v4.15"
        if tag in self.repo.references:
            LOGGER.info("Skipping commits before tag '%s'!", tag)
            base_commit = self.repo.commit(tag)
        else:
            LOGGER.warning("Tag '%s' not in local repo, not limiting commits by age", tag)
            base_commit = None
        missing_commits = [
            commit
            for commit in list(db_commits.keys() - wb_commits)
            if self.include_commit(commit, base_commit)
        ]

        # Append each missing commit as a new row to the commits worksheet.
        LOGGER.info("Exporting %d commits to %s", len(missing_commits), out_file)
        for commit in missing_commits:
            worksheet.append(self.create_commit_row(commit, worksheet))

        workbook.save(out_file)
        LOGGER.info("Finished exporting!")

    def get_distros(self) -> List[str]:
        """Collect the distros we’re tracking in the database."""
        with self.database.get_session() as session:
            # TODO (Issue 51): Handle Debian.
            return [
                distro
                for (distro,) in session.query(Distros.distroID)
                if not distro.startswith("Debian")
            ]

    def get_fixed_patches(self, commit: str, commits: Dict[str, int]) -> str:
        """Get the fixed patches for the given commit."""
        with self.database.get_session() as session:
            patch = session.query(PatchData).filter_by(patchID=commits[commit]).one()
            # The database stores these separated by a space, but we want commas in the spreadsheet.
            return ", ".join(patch.fixedPatches.split()) if patch.fixedPatches else None

    def get_revision(self, distro: str, commit: str, commits: Dict[str, int]) -> str:
        """Get the kernel revision which includes commit or 'Absent'."""
        # NOTE: For some distros (e.g. Ubuntu), we continually add new revisions (Git tags) as they
        # become available, so we need the max ID, which is the most recent.
        with self.database.get_session() as session:
            subject, _ = (
                session.query(
                    MonitoringSubjects,
                    sqlalchemy.func.max(MonitoringSubjects.monitoringSubjectID),
                )
                .filter_by(distroID=distro)
                .one()
            )

            # TODO (Issue 40): We could try to simplify this using the ‘monitoringSubject’
            # relationship on the ‘PatchData’ table, but because the database tracks what’s missing,
            # it becomes hard to state where the patch is present.
            missing_patch = subject.missingPatches.filter_by(patchID=commits[commit]).one_or_none()

            return subject.revision if missing_patch is None else "Absent"

    def update_commits(self, in_file: str, out_file: str) -> None:
        """Update each row with the 'Fixes' and distro information."""
        workbook, worksheet = get_workbook(in_file)
        commits = self.get_db_commits()
        distros = self.get_distros()
        for distro in distros:
            try:
                get_column(worksheet, distro)
            except StopIteration:
                LOGGER.error("No column with distro '%s', please fix spreadsheet!", distro)
                sys.exit(1)

        commit_column = get_column(worksheet, "Commit ID").column_letter

        for commit_cell in worksheet[commit_column][1:]:  # Skip the header row
            commit = commit_cell.value
            if commit is None:
                continue  # Ignore empty rows.

            # Update “Fixes” column.
            if commit in commits:
                get_cell(worksheet, "Fixes", commit_cell.row).value = self.get_fixed_patches(
                    commit, commits
                )

            # Update all distro columns.
            for distro in distros:
                if commit in commits:
                    get_cell(worksheet, distro, commit_cell.row).value = self.get_revision(
                        distro, commit, commits
                    )
                else:
                    get_cell(worksheet, distro, commit_cell.row).value = "Unknown"

        workbook.save(out_file)
        LOGGER.info("Finished updating!")
