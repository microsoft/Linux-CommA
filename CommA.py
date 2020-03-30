#!/usr/bin/env python3
import argparse

import Util.Config
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.SqlClasses import Distros
from DownstreamTracker.MonitorDownstream import monitor_downstream
from UpstreamTracker.MonitorUpstream import monitor_upstream

parser = argparse.ArgumentParser(description="Linux Commit Analyzer.")
parser.add_argument(
    "-n",
    "--dry-run",
    action="store_true",
    help="Do not connect to production database.",
)
parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Print verbose information, such as queries.",
)

subparsers = parser.add_subparsers(title="subcommands")


def run(args):
    if args.dry_run:
        with DatabaseDriver.get_session() as s:
            if s.query(Distros).first() is None:
                s.add_all(Util.Config.default_distros)
    if args.upstream:
        monitor_upstream()
    if args.downstream:
        monitor_downstream()


run_parser = subparsers.add_parser("run", help="Analyze commits in Linux repos.")
run_parser.add_argument(
    "-u", "--upstream", action="store_true", help="Monitor the upstream patches."
)
run_parser.add_argument(
    "-d", "--downstream", action="store_true", help="Monitor the downstream patches."
)
run_parser.set_defaults(func=run)


def add_distro(args):
    with DatabaseDriver.get_session() as s:
        s.add(Distros(distroID=args.name, repoLink=args.url))


distro_parser = subparsers.add_parser(
    "add-distro", help="Add a distro to the database."
)
distro_parser.add_argument(
    "-n",
    "--name",
    required=True,
    help="Database name (ID) for distro, e.g. 'Ubuntu18.04'.",
)
distro_parser.add_argument(
    "-u",
    "--url",
    required=True,
    help="Git repository URL for distro, e.g. 'https://git.launchpad.net/...'.",
)
distro_parser.set_defaults(func=add_distro)


if __name__ == "__main__":
    print("Welcome to Patch tracker!")
    args = parser.parse_args()
    Util.Config.dry_run = args.dry_run
    Util.Config.verbose = args.verbose
    args.func(args)
