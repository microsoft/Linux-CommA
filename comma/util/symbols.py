# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions for generating symbol maps
"""

import logging
import subprocess

from comma.database.driver import DatabaseDriver
from comma.database.model import PatchData
from comma.util.tracking import get_linux_repo


LOGGER = logging.getLogger(__name__)


def get_symbols(repo_dir, files):
    """
    get_symbols: This function returns a list of symbols for given files
    files: HyperV files list
    @return symbol_list: list of symbols generated through ctags
    """
    command = "ctags -R -x −−c−kinds=f {}".format(
        " ".join(files) + " | awk '{ if ($2 == \"function\") print $1 }'"
    )
    LOGGER.debug("Running command: %s", command)
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        check=True,
        universal_newlines=True,
    )
    return process.stdout.splitlines()


def map_symbols_to_patch(
    repo, commits, files, prev_commit="097c1bd5673edaf2a162724636858b71f658fdd2"
):
    """
    This function generates and stores symbols generated by each patch
    repo: git repo object
    files: hyperV files
    commits: SHA of all commits in database
    prev_commit: SHA of start of HyperV patch to track
    """

    # Preserve initial reference
    initial_reference = repo.head.reference

    try:
        repo.head.reference = repo.commit(prev_commit)
        repo.head.reset(index=True, working_tree=True)
        before_patch_apply = None

        # Iterate through commits
        for commit in commits:
            # Get symbols before patch is applied
            if before_patch_apply is None:
                before_patch_apply = set(get_symbols(repo.working_tree_dir, files))

            # Checkout commit
            repo.head.reference = repo.commit(commit)
            repo.head.reset(index=True, working_tree=True)

            # Get symbols after patch is applied
            after_patch_apply = set(get_symbols(repo.working_tree_dir, files))

            # Compare symbols before and after patch
            diff_symbols = after_patch_apply - before_patch_apply
            print(f"Commit: {commit} -> {''.join(diff_symbols)}")

            # Save symbols to database
            with DatabaseDriver.get_session() as session:
                patch = session.query(PatchData).filter_by(commitID=commit).one()
                patch.symbols = " ".join(diff_symbols)

            # Use symbols from current commit to compare to next commit
            before_patch_apply = after_patch_apply

    finally:
        # Reset reference
        repo.head.reference = initial_reference
        repo.head.reset(index=True, working_tree=True)


def get_hyperv_patch_symbols():
    """
    This function clones upstream and gets upstream commits, hyperV files
    """

    repo = get_linux_repo(name="linux-sym", shallow=False, pull=True)

    with DatabaseDriver.get_session() as session:
        # SQLAlchemy returns tuples which need to be unwrapped
        map_symbols_to_patch(
            repo,
            [
                commit[0]
                for commit in session.query(PatchData.commitID).order_by(PatchData.commitTime).all()
            ],
            repo.get_tracked_paths(),
        )


def symbol_checker(symbol_file):
    """
    This function returns missing symbols by comparing database patch symbols with given symbols
    symbol_file: file containing symbols to run against database
    return missing_symbols_patch: list of missing symbols from given list
    """
    symbols_in_file = {line.strip() for line in symbol_file}
    symbol_file.close()
    with DatabaseDriver.get_session() as session:
        return sorted(
            patch_id
            for patch_id, symbols in session.query(PatchData.patchID, PatchData.symbols)
            .filter(PatchData.symbols != " ")
            .order_by(PatchData.commitTime)
            .all()
            if len(set(symbols.split(" ")) - symbols_in_file) > 0
        )
