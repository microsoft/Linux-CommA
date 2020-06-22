# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import logging

from UpstreamTracker.ParseData import process_commits
from Util.Tracking import get_repo, get_tracked_paths


def monitor_upstream():
    print("Monitoring upstream...")
    logging.info("Starting patch scraping from files...")
    process_commits(get_repo(), get_tracked_paths(), add_to_database=True)
    print("Finishing monitoring upstream!")
