import logging
import subprocess
from pathlib import Path

from git import Repo

import Util.Constants as cst
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.SqlClasses import PatchData
from UpstreamTracker.MonitorUpstream import get_hyperv_filenames
from Util.util import list_diff


def get_symbols(repo_dir, files):
    """
    get_symbols: This function returns a list of symbols for given files
    files: HyperV files list
    @return symbol_list: list of symbols generated through ctags
    """
    command = "ctags -R -x −−c−kinds=f {}".format(
        " ".join(files) + " | awk '{ if ($2 == \"function\") print $1 }'"
    )
    logging.debug("Running command: " + command)
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        check=True,
        universal_newlines=True,
    )
    symbol_list = process.stdout.splitlines()
    return symbol_list


def map_symbols_to_patch(
    repo, commits, files, prev_commit="097c1bd5673edaf2a162724636858b71f658fdd2"
):
    """
    This function generates and stores symbols generated by each patch
    prev_commit : SHA of start of HyperV patchTo track symbols generated by current patch we compare symbols generated
    by last commit to this commit symbols.
    commits: SHA of all commits in database
    fileNames: hyperV files
    """
    repo.head.reference = repo.commit(prev_commit)
    repo.head.reset(index=True, working_tree=True)
    before_patch_apply = None
    # iterate
    for commit in commits:
        # get symbols
        if before_patch_apply is None:
            before_patch_apply = get_symbols(repo.working_tree_dir, files)

        repo.head.reference = repo.commit(commit)
        repo.head.reset(index=True, working_tree=True)

        after_patch_apply = get_symbols(repo.working_tree_dir, files)

        # compare
        diff_symbols = list_diff(after_patch_apply, before_patch_apply)
        print("Commit: " + commit + " -> " + "".join(diff_symbols))

        # save symbols into database
        with DatabaseDriver.get_session() as s:
            patch = s.query(PatchData).filter_by(commitID=commit).one()
            patch.symbols = " ".join(diff_symbols)
        before_patch_apply = after_patch_apply


def get_hyperv_patch_symbols():
    """
    This function clones upstream and gets upstream commits, hyperV files
    """
    repo_path = Path(cst.PATH_TO_REPOS, cst.LINUX_SYMBOL_REPO_NAME).resolve()
    if repo_path.exists():
        repo = Repo(repo_path)
        logging.info("Fetching Linux symbol checkout...")
        repo.git.fetch()
        logging.info("Fetched!")
    else:
        # TODO: Return this code when we fix the issue with shallow fetch.
        # upstream_repo_path = Path(cst.PATH_TO_REPOS, cst.LINUX_REPO_NAME).resolve()
        source_repo = (
            # upstream_repo_path
            # if upstream_repo_path.exists()
            # else
            "https://github.com/torvalds/linux.git"
        )
        logging.info(f"Cloning Linux symbol checkout from '{source_repo}'")
        repo = Repo.clone_from("https://github.com/torvalds/linux.git", repo_path)
        logging.info("Cloned!")

    logging.debug("Parsing maintainers files...")
    filenames = get_hyperv_filenames(repo, "origin/master")
    assert filenames is not None
    logging.debug("Parsed!")

    with DatabaseDriver.get_session() as s:
        # Only annoying thing with SQLAlchemy is that this always
        # returns tuples which we need to unwrap.
        commits = [
            c for c, in s.query(PatchData.commitID).order_by(PatchData.commitTime).all()
        ]
        map_symbols_to_patch(repo, commits, filenames)


def symbol_checker(symbol_file):
    """
    This function returns missing symbols by comparing database patch symbols with given symbols
    symbol_file: file containing symbols to run against database
    return missing_symbols_patch: list of missing symbols from given list
    """
    list_of_symbols = [line.strip() for line in symbol_file]
    symbol_file.close()
    with DatabaseDriver.get_session() as s:
        symbols = (
            s.query(PatchData.patchID, PatchData.symbols)
            .filter(PatchData.symbols != " ")
            .order_by(PatchData.commitTime)
            .all()
        )
        symbol_map = dict((p, s.split(" ")) for p, s in symbols)
        missing_symbol_patch = []
        for patchID, symbols in symbol_map.items():
            if len(list_diff(symbols, list_of_symbols)) > 0:
                missing_symbol_patch.append(patchID)
        return sorted(missing_symbol_patch)


def print_missing_symbols(symbol_file):
    print("Starting the Symbol Checker...")
    get_hyperv_patch_symbols()
    missing_symbols = symbol_checker(symbol_file)
    print("Missing symbols:")
    print(*missing_symbols)
