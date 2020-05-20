import logging
from pathlib import Path

from git import Repo

import Util.Config
import Util.Constants as cst
from Util.Tracking import get_tracked_paths
from UpstreamTracker.ParseData import process_commits


def monitor_upstream():
    print("Monitoring upstream...")
    logging.info("Starting patch scraping from files..")
    repo_path = Path(cst.PATH_TO_REPOS, cst.LINUX_REPO_NAME).resolve()
    if repo_path.exists():
        repo = Repo(repo_path)
        if Util.Config.fetch:
            logging.info("Fetching Linux repo...")
            repo.git.fetch(
                "--all", "--tags", "--force", f"--shallow-since={Util.Config.since}",
            )
            logging.info("Fetched!")
    else:
        logging.info("Cloning Linux repo...")
        # TODO add functionality for multiple upstream repos (namely linux-next, linux-mainstream, and linux-stable)
        repo = Repo.clone_from(
            cst.LINUX_REPO_URL, repo_path, bare=True, shallow_since=Util.Config.since,
        )
        logging.info("Cloned!")

    # TODO Make last sha work, get last sha given repo+reference we have
    # if os.path.exists(cst.PATH_TO_LAST_SHA) and out.split()[0] == open(cst.PATH_TO_LAST_SHA).read():
    #     print("[Info] No new commits found")
    # else:
    #     print("[Info] New commits found")
    logging.debug("Starting commit parsing")
    process_commits(repo, "master", get_tracked_paths(repo), add_to_database=True)
    print("Finishing monitoring upstream!")
