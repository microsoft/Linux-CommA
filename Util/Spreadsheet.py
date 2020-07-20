# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import git
import openpyxl
import sqlalchemy
from openpyxl.cell import cell
from openpyxl.workbook import workbook
from openpyxl.worksheet import worksheet

import Util.Config
import Util.Tracking
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.SqlClasses import Distros, MonitoringSubjects, PatchData
from UpstreamTracker.ParseData import process_commits


def get_db_commits() -> Dict[str, int]:
    """Query the 'PatchData' table for all commit hashes and IDs."""
    with DatabaseDriver.get_session() as s:  # type: sqlalchemy.orm.session.Session
        return {
            commit_id: patch_id
            for (commit_id, patch_id) in s.query(
                PatchData.commitID, PatchData.patchID
            ).filter(
                # Exclude ~1000 CIFS patches.
                ~PatchData.affectedFilenames.like("%fs/cifs%")
            )
        }


def get_workbook(in_file: str) -> Tuple[workbook.Workbook, worksheet.Worksheet]:
    if not Path(in_file).exists():
        logging.error(f"The file {in_file} does not exist")
        sys.exit(1)
    wb = openpyxl.load_workbook(filename=in_file)
    # Force refresh of pivot table in “Pivot” worksheet.
    pivot = wb["Pivot"]._pivots[0]
    pivot.cache.refreshOnLoad = True
    # The worksheet is manually named “git log”.
    ws = wb["git log"]
    return (wb, ws)


def get_wb_commits(ws: worksheet.Worksheet) -> Set[str]:
    # Skip the header and all ‘None’ values.
    return {c.value for c in ws["A"][1:] if c.value is not None}


def import_commits(in_file: str) -> None:
    """This adds commits from the spreadsheet into the database.

    This lets us track additional commits that were manually added to
    the spreadsheet, but were not automatically found by CommA's
    upstream monitoring logic.

    """
    print(f"Importing commits from spreadsheet '{in_file}'...")
    wb, ws = get_workbook(in_file)
    wb_commits = get_wb_commits(ws)
    db_commits = get_db_commits()
    missing_commits = wb_commits - db_commits.keys()
    process_commits(commit_ids=missing_commits, add_to_database=True)
    print("Finished importing!")


def include_commit(sha: str, repo: git.Repo, base_commit: git.Commit) -> bool:
    """Determine if we should export the commit."""
    # Skip empty values (such as if ‘cell.value’ was passed).
    if sha is None:
        return False
    # Skip commits that aren’t in the repo.
    try:
        commit = repo.commit(sha)
    except ValueError:
        return False
    # Skip commits before the chosen base.
    if not repo.is_ancestor(base_commit, commit):
        return False
    # Skip commits to tools.
    filenames = Util.Tracking.get_filenames(commit)
    if any(f.startswith("tools/hv/") for f in filenames):
        return False
    return True


def create_commit_row(sha: str, repo: git.Repo) -> Dict[str, Any]:
    """Create a row with the commit's SHA, date, release and title."""
    # TODO: Add a column with the “fixes” info.
    commit = repo.commit(sha)
    date = datetime.utcfromtimestamp(commit.authored_date).date()
    title = commit.message.split("\n")[0]
    # Get the ‘v5.7’ from ‘v5.7-rc1-2-gc81992e7f’.
    # NOTE: This must be ordered “--contains <SHA>” for Git.
    tag = repo.git.describe("--contains", sha)
    release = re.search(r"(v[^-~]*)[-~]", tag).group(1)
    # The worksheet has additional columns with manually entered
    # info, which we can’t insert, so we skip them.
    return {
        "A": sha,
        "B": date,
        "C": release,
        "G": title[: min(len(title), 120)],
    }


def export_commits(in_file: str, out_file: str) -> None:
    """This adds commits from the database to the spreadsheet.

    This lets us automatically update the spreadsheet by adding
    commits which CommA found. It adds the basic information available
    from the commit.

    """
    wb, ws = get_workbook(in_file)
    wb_commits = get_wb_commits(ws)

    # Collect the commits in the database which are not in the
    # workbook, but that we want to include.
    db_commits = get_db_commits()
    repo = Util.Tracking.get_linux_repo()
    base_commit = repo.commit("v4.11")
    missing_commits = [
        commit
        for commit in list(db_commits.keys() - wb_commits)
        if include_commit(commit, repo, base_commit)
    ]

    # Append each missing commit as a new row to the commits
    # worksheet.
    print(f"Exporting {len(missing_commits)} commits to {out_file}...")
    for commit in missing_commits:
        # TODO: Set fonts of the cells.
        ws.append(create_commit_row(commit, repo))
    wb.save(out_file)
    print("Finished exporting!")


def create_distros_row(
    c: cell.Cell, commits: Dict[str, int], distros: List[str]
) -> List[str]:
    """Create a row with every distro's status of the cell's commit."""
    # Excel XLOOPUP to make this a reference: ='git log'!A3
    row = [f"='{c.parent.title}'!{c.coordinate}"]
    commit = c.value
    with DatabaseDriver.get_session() as s:
        for distro in distros:
            if commit not in commits:
                row.append("Unknown")
                continue
            # NOTE: For some distros (e.g. Ubuntu), we continually add
            # new revisions (Git tags) as they become available, so we
            # need the max ID, which is the most recent.
            subject, _ = (
                s.query(
                    MonitoringSubjects,
                    sqlalchemy.func.max(MonitoringSubjects.monitoringSubjectID),
                )
                .filter_by(distroID=distro)
                .one()
            )
            # TODO: We could try to simplify this using the
            # ‘monitoringSubject’ relationship on the ‘PatchData’
            # table, but because the database tracks what’s missing,
            # it becomes hard to state where the patch is present.
            missing_patch = subject.missingPatches.filter_by(
                patchID=commits[commit]
            ).one_or_none()
            if missing_patch is None:  # Then it’s present.
                row.append(subject.revision)
            else:
                row.append("Absent")
    return row


def export_distros(in_file: str, out_file: str) -> None:
    """This adds a worksheet with downstream distro statuses."""
    wb, ws = get_workbook(in_file)

    # Collect the distros we’re tracking in the database.
    with DatabaseDriver.get_session() as s:
        distros = [d for (d,) in s.query(Distros.distroID)]

    # Create the distros worksheet with a header.
    distros_ws = wb.create_sheet("distros")
    # TODO: Make this a real header with fonts.
    distros_ws.append(["Commit ID"] + distros)

    commits = get_db_commits()
    for c in ws["A"][1:]:  # Ignore header.
        if c.value:  # Ignore empty cells.
            distros_ws.append(create_distros_row(c, commits, distros))
    wb.save(out_file)
