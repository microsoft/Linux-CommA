# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import logging

from comma.upstream.parser import process_commits


def monitor_upstream():
    print("Monitoring upstream...")
    logging.info("Starting patch scraping from files...")
    process_commits(add_to_database=True)
    print("Finishing monitoring upstream!")
