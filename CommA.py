#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import argparse
import logging

import Util.Config
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.SqlClasses import Distros, MonitoringSubjects
from DownstreamTracker.MonitorDownstream import monitor_downstream
from UpstreamTracker.MonitorUpstream import monitor_upstream
from Util.Spreadsheet import export_commits, import_commits, update_commits
from Util.Symbols import print_missing_symbols
from Util.Tracking import print_tracked_paths

# TODO: We have a lot of parsers and could refactor them into their
# own modules.
parser = argparse.ArgumentParser(description="Linux Commit Analyzer.")
parser.add_argument(
    "-n",
    "--dry-run",
    action="store_true",
    help="Do not connect to production database.",
)
parser.add_argument(
    "-v", "--verbose", action="count", default=0, help="increase output verbosity",
)
parser.add_argument(
    "--no-fetch",
    action="store_true",
    help="Do not fetch Git repos (used by developers).",
)
parser.add_argument(
    "-s",
    "--since",
    action="store",
    default=Util.Config.since,
    help=f"Parameter to pass to underlying Git commands, default is '{Util.Config.since}'.",
)

subparsers = parser.add_subparsers(title="subcommands")


def run(args):
    if args.dry_run:
        with DatabaseDriver.get_session() as s:
            if s.query(Distros).first() is None:
                s.add_all(Util.Config.default_distros)
            if s.query(MonitoringSubjects).first() is None:
                s.add_all(Util.Config.default_monitoring_subjects)
    if args.section:
        Util.Config.sections = args.section
    if args.print_tracked_paths:
        print_tracked_paths()
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
run_parser.add_argument(
    "-p",
    "--print-tracked-paths",
    action="store_true",
    help="Print the paths that would be analyzed.",
)
run_parser.add_argument(
    "-s",
    "--section",
    action="append",
    default=Util.Config.sections,
    help="List of kernel section entries in MAINTAINERS file to analyze.",
)
run_parser.set_defaults(func=run)

symbol_parser = subparsers.add_parser(
    "print-symbols", help="Compare symbols against patches."
)
symbol_parser.add_argument(
    "-f",
    "--file",
    type=argparse.FileType("r"),
    default="symbols.txt",
    help="File with symbols to compare against.",
)
symbol_parser.set_defaults(func=(lambda args: print_missing_symbols(args.file)))


def spreadsheet(args):
    if args.import_commits:
        import_commits(args.in_file)
    if args.export_commits:
        export_commits(args.in_file, args.out_file)
    if args.update_commits:
        update_commits(args.in_file, args.out_file)


spreadsheet_parser = subparsers.add_parser(
    "spreadsheet", help="Export to Excel Spreadsheet.",
)
spreadsheet_parser.add_argument(
    "-i",
    "--import-commits",
    action="store_true",
    help="Import commits from spreadsheet into database.",
)
spreadsheet_parser.add_argument(
    "-e",
    "--export-commits",
    action="store_true",
    help="Export commits from database into spreadsheet.",
)
spreadsheet_parser.add_argument(
    "-u",
    "--update-commits",
    action="store_true",
    help="Export downstream distro statuses from database into spreadsheet.",
)
spreadsheet_parser.add_argument(
    "-f", "--in-file", default="input.xlsx", help="Spreadsheet to read in.",
)
spreadsheet_parser.add_argument(
    "-o", "--out-file", default="output.xlsx", help="Spreadsheet to write out.",
)
spreadsheet_parser.set_defaults(func=spreadsheet)


def get_distros(args):
    with DatabaseDriver.get_session() as s:
        print("DistroID\tRevision")
        for distro, revision in (
            s.query(Distros.distroID, MonitoringSubjects.revision)
            .outerjoin(
                MonitoringSubjects, Distros.distroID == MonitoringSubjects.distroID
            )
            .all()
        ):
            print(f"{distro}\t{revision}")
    logging.debug("Successfully printed revisions")


print_distro_parser = subparsers.add_parser(
    "print-distros", help="Print current <distro-name, revision> info.",
)
print_distro_parser.set_defaults(func=get_distros)


def add_distro(args):
    with DatabaseDriver.get_session() as s:
        s.add(Distros(distroID=args.name, repoLink=args.url))
        s.add(MonitoringSubjects(distroID=args.name, revision=args.revision))
    logging.info(f"Successfully added new distro: {args.name}")


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
distro_parser.add_argument(
    "-r",
    "--revision",
    required=True,
    help="Repository revision to track. For adding a new branch use distro-name/branch-name format. e.g. 'SUSE12/SUSE12-SP5-AZURE'.",
)
distro_parser.set_defaults(func=add_distro)


def add_kernel(args):
    with DatabaseDriver.get_session() as s:
        s.add(MonitoringSubjects(distroID=args.name, revision=args.revision))
    logging.info(
        f"Successfully added new revision '{args.revision}' for distro '{args.name}'"
    )


kernel_parser = subparsers.add_parser(
    "add-kernel", help="Add new kernel/revision to track for pre-existing distros."
)
kernel_parser.add_argument(
    "-n",
    "--name",
    required=True,
    help="Database name (ID) for distro, e.g. 'Ubuntu18.04'",
)
kernel_parser.add_argument(
    "-r",
    "--revision",
    required=True,
    help="Repository revision to track. For adding a new branch use distro-name/branch-name format. e.g. SUSE12/SUSE12-SP5-AZURE",
)
kernel_parser.set_defaults(func=add_kernel)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(name)-5s %(levelname)-7s %(message)s",
    datefmt="%m-%d %H:%M",
)


if __name__ == "__main__":
    args = parser.parse_args()
    Util.Config.verbose = args.verbose
    logging_level = (
        logging.WARNING
        if Util.Config.verbose == 0
        else logging.INFO
        if Util.Config.verbose == 1
        else logging.DEBUG
    )
    logging.getLogger().setLevel(logging_level)
    Util.Config.dry_run = args.dry_run
    Util.Config.since = args.since
    Util.Config.fetch = not args.no_fetch
    print("Welcome to Commit Analyzer!")
    args.func(args)
    print("Commit Analyzer completed!")
