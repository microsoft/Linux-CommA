#!/usr/bin/env python3
import argparse
from UpstreamTracker.MonitorUpstream import monitor_upstream
from DownstreamTracker.MonitorDownstream import monitor_downstream

parser = argparse.ArgumentParser(description="Linux Commit Analyzer.")
parser.add_argument(
    "--upstream", action="store_true", help="Monitor the upstream patches."
)
parser.add_argument(
    "--downstream", action="store_true", help="Monitor the downstream patches."
)

if __name__ == "__main__":
    print("Welcome to Patch tracker!")
    args = parser.parse_args()
    if args.upstream:
        monitor_upstream()
    if args.downstream:
        monitor_downstream()
