# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions for exporting data to Excel spreadsheets
"""

import logging
import re
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import git
import openpyxl
from openpyxl.cell.cell import Cell
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from comma.database.model import MonitoringSubjects, PatchData


LOGGER = logging.getLogger(__name__)


class WorksheetWrapper:
    """
    Wrapper for openpyxl worksheet
    Consolidates common worksheet logic
    """

    def __init__(self, worksheet: Worksheet) -> None:
        self.worksheet = worksheet

    @lru_cache  # noqa: B019
    def get_column(self, name: str) -> int:
        """Get column by letter"""
        return next(cell for cell in self.worksheet[1] if cell.value == name).column

    def get_column_cells(self, name: str) -> List[Cell]:
        """Get cells for a specified column if the cell has a value"""

        column = self.get_column(name)
        return tuple(
            cell
            for cell in next(self.worksheet.iter_cols(min_row=2, min_col=column, max_col=column))
            if cell.value is not None
        )

    def get_cell(self, name: str, row) -> Cell:
        """Get the cell of the named column in this commit's row."""
        return self.worksheet.cell(row, self.get_column(name))

    def append(self, row: Dict[str, Any]) -> None:
        """
        Given a dictionary with column headers as rows, format and append to worksheet
        """
        self.worksheet.append({self.get_column(key): value for key, value in row.items()})


def get_workbook(in_file: str) -> Tuple[Workbook, WorksheetWrapper]:
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

    return (workbook, WorksheetWrapper(worksheet))


class Spreadsheet:
    """
    Parent object for symbol operations
    """

    def __init__(self, config, database, repo) -> None:
        self.config = config
        self.database = database
        self.repo = repo

    def get_db_commits(
        self, since: Optional[float] = None, exclude_files: Optional[Iterable[str]] = None
    ) -> Dict[str, int]:
        """Query the 'PatchData' table for all commit hashes and IDs."""
        with self.database.get_session() as session:
            query = session.query(PatchData.commitID, PatchData.patchID)

            if exclude_files:
                for entry in exclude_files:
                    query = query.filter(~PatchData.affectedFilenames.like(entry))

            if since:
                query = query.filter(PatchData.commitTime >= since)

            return dict(query)

    def include_commit(self, sha: str) -> bool:
        """Determine if we should export the commit."""

        # Skip empty values (such as if ‘cell.value’ was passed).
        if sha is None:
            LOGGER.warning("Given SHA was 'None'!")
            return False

        # Skip commits that are not in the repo.
        try:
            self.repo.commit(sha)
        except ValueError:
            LOGGER.warning("Commit '%s' not in repo!", sha)
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

    def export_commits(self, in_file: str, out_file: str) -> None:
        """This adds commits from the database to the spreadsheet.

        This lets us automatically update the spreadsheet by adding commits which CommA found.
        It adds the basic information available from the commit.

        """
        workbook, worksheet = get_workbook(in_file)
        wb_commits = {cell.value for cell in worksheet.get_column_cells("Commit ID")}

        # Collect the commits in the database and not in the workbook, but that we want to include.
        # Exclude ~1000 CIFS patches and anything that touches tools/hv  # pylint: disable=wrong-spelling-in-comment
        db_commits = self.get_db_commits(
            since=self.config.upstream_since.epoch, exclude_files=("%fs/cifs%", "%tools/hv/%")
        )
        missing_commits = [
            commit for commit in list(db_commits.keys() - wb_commits) if self.include_commit(commit)
        ]

        # Append each missing commit as a new row to the commits worksheet.
        LOGGER.info("Exporting %d commits to %s", len(missing_commits), out_file)
        for sha in missing_commits:
            # TODO (Issue 40): If release was added to the database, commit could be skipped and
            # all data could be pulled from the database
            commit = self.repo.commit(sha)
            worksheet.append(
                {
                    "Commit ID": sha,
                    "Date": datetime.utcfromtimestamp(commit.authored_date).date(),
                    "Release": self.get_release(sha),
                    "Commit Title": "{:.120}".format(commit.message.split("\n")[0]),
                }
            )

        workbook.save(out_file)
        LOGGER.info("Finished exporting!")

    def update_commits(self, in_file: str, out_file: str) -> None:
        # pylint: disable=too-many-locals
        """Update each row with the 'Fixes' and distro information."""
        workbook, worksheet = get_workbook(in_file)
        # Exclude ~1000 CIFS patches
        db_commits = self.get_db_commits(exclude_files=("%fs/cifs%",))
        targets = {}

        with self.database.get_session() as session:
            for repo in self.database.get_downstream_repos():
                # TODO (Issue 51): Handle Debian
                if repo.startswith("Debian"):
                    continue

                # Make sure there is a column in the spreadsheet
                try:
                    worksheet.get_column(repo)
                except StopIteration:
                    LOGGER.error("No column with distro '%s', please fix spreadsheet!", repo)
                    sys.exit(1)

                # Get the latest monitoring subject for the remote
                targets[repo] = (
                    session.query(MonitoringSubjects)
                    .filter_by(distroID=repo)
                    .order_by(MonitoringSubjects.monitoringSubjectID.desc())
                    .limit(1)
                    .one()
                )

            commits_cells = worksheet.get_column_cells("Commit ID")
            total_rows = len(commits_cells)
            LOGGER.info("Evaluating updates for %d rows", total_rows)

            # Iterate through commit IDs in spreadsheet. Skip the header row.
            for count, commit_cell in enumerate(commits_cells):
                if count and not count % 50:
                    LOGGER.info("Evaluated updates for %d of %d rows", count, total_rows)

                patch_id = db_commits.get(commit_cell.value)

                # If patch isn't in the database, set all distros to unknown
                if patch_id is None:
                    for distro in targets:
                        worksheet.get_cell(distro, commit_cell.row).value = "Unknown"
                    continue

                # Update “Fixes” column.
                patch = session.query(PatchData).filter_by(patchID=patch_id).one()
                # The database stores these separated by a space, but we want commas
                worksheet.get_cell("Fixes", commit_cell.row).value = (
                    ", ".join(patch.fixedPatches.split()) if patch.fixedPatches else None
                )

                # Update all distro columns.
                for distro, subject in targets.items():
                    # TODO (Issue 40): We could try to simplify this using the monitoringSubject
                    # relationship on the PatchData table, but because the database tracks
                    # what’s missing, it becomes hard to state where the patch is present.
                    missing_patch = subject.missingPatches.filter_by(patchID=patch_id).one_or_none()
                    worksheet.get_cell(distro, commit_cell.row).value = (
                        subject.revision if missing_patch is None else "Absent"
                    )

            LOGGER.info("Updates evaluated for %s rows", total_rows)

            workbook.save(out_file)
            LOGGER.info("Finished updating!")
