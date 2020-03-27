#!/usr/bin/env python3
import argparse

import Util.Config
from DownstreamTracker.MonitorDownstream import monitor_downstream
from UpstreamTracker.MonitorUpstream import monitor_upstream

parser = argparse.ArgumentParser(description="Linux Commit Analyzer.")
parser.add_argument(
    "--upstream", action="store_true", help="Monitor the upstream patches."
)
parser.add_argument(
    "--downstream", action="store_true", help="Monitor the downstream patches."
)
parser.add_argument(
    "--dry-run", action="store_true", help="Do not connect to production database."
)

if __name__ == "__main__":
    print("Welcome to Patch tracker!")
    args = parser.parse_args()
    Util.Config.dry_run = args.dry_run
    if args.upstream:
        monitor_upstream()
    if args.downstream:
        monitor_downstream()
