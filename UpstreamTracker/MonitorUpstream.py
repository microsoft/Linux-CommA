import logging

from UpstreamTracker.ParseData import process_commits
from Util.Tracking import get_repo, get_tracked_paths


def monitor_upstream():
    print("Monitoring upstream...")
    logging.info("Starting patch scraping from files..")

    # TODO Make last sha work, get last sha given repo+reference we have
    # if os.path.exists(cst.PATH_TO_LAST_SHA) and out.split()[0] == open(cst.PATH_TO_LAST_SHA).read():
    #     print("[Info] No new commits found")
    # else:
    #     print("[Info] New commits found")
    logging.debug("Starting commit parsing")
    process_commits(repo, "master", get_tracked_paths(repo), add_to_database=True)
    print("Finishing monitoring upstream!")
