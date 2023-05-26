#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Main entry point for program
"""

import argparse
import logging
from typing import Optional

from comma.database.driver import DatabaseDriver
from comma.database.model import Distros, MonitoringSubjects
from comma.downstream.monitor import monitor_downstream
from comma.upstream import process_commits
from comma.util import config
from comma.util.spreadsheet import export_commits, import_commits, update_commits
from comma.util.symbols import print_missing_symbols
from comma.util.tracking import print_tracked_paths


def run(args):
    """
    Analyze commits
    """

    if args.dry_run:
        with DatabaseDriver.get_session() as session:
            if session.query(Distros).first() is None:
                session.add_all(config.default_distros)
            if session.query(MonitoringSubjects).first() is None:
                session.add_all(config.default_monitoring_subjects)
    if args.section:
        config.sections = args.section
    if args.print_tracked_paths:
        print_tracked_paths()
    if args.upstream:
        print("Monitoring upstream...")
        logging.info("Starting patch scraping from files...")
        process_commits(add_to_database=True)
        print("Finishing monitoring upstream!")
    if args.downstream:
        monitor_downstream()


def spreadsheet(args):
    """
    Export data to an Excel spreadsheet
    """

    if args.import_commits:
        import_commits(args.in_file)
    if args.export_commits:
        export_commits(args.in_file, args.out_file)
    if args.update_commits:
        update_commits(args.in_file, args.out_file)


def get_distros():
    """
    Print distro and references being tracked
    """

    with DatabaseDriver.get_session() as session:
        print("DistroID\tRevision")
        for distro, revision in (
            session.query(Distros.distroID, MonitoringSubjects.revision)
            .outerjoin(MonitoringSubjects, Distros.distroID == MonitoringSubjects.distroID)
            .all()
        ):
            print(f"{distro}\t{revision}")
    logging.debug("Successfully printed revisions")


def add_distro(args):
    """
    Add a disto to the the database
    """

    with DatabaseDriver.get_session() as session:
        session.add(Distros(distroID=args.name, repoLink=args.url))
        session.add(MonitoringSubjects(distroID=args.name, revision=args.revision))
    logging.info("Successfully added new distro: %s", {args.name})


def add_kernel(args):
    """
    Add a reference to track for an existing distro
    """

    with DatabaseDriver.get_session() as session:
        session.add(MonitoringSubjects(distroID=args.name, revision=args.revision))
    logging.info("Successfully added new revision '%s' for distro '%s'", args.revision, args.name)


def get_cli_options(args: Optional[str] = None) -> argparse.Namespace:
    """
    Parse CLI options and return a namespace
    """

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
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase output verbosity",
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
        default=config.since,
        help=f"Parameter to pass to underlying Git commands, default is '{config.since}'.",
    )

    subparsers = parser.add_subparsers(title="subcommands")

    run_parser = subparsers.add_parser("run", help="Analyze commits in Linux repos.")
    run_parser.add_argument(
        "-u", "--upstream", action="store_true", help="Monitor the upstream patches."
    )
    run_parser.add_argument(
        "-d",
        "--downstream",
        action="store_true",
        help="Monitor the downstream patches.",
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
        default=config.sections,
        help="List of kernel section entries in MAINTAINERS file to analyze.",
    )
    run_parser.set_defaults(func=run)

    symbol_parser = subparsers.add_parser("print-symbols", help="Compare symbols against patches.")
    symbol_parser.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("r"),
        default="symbols.txt",
        help="File with symbols to compare against.",
    )
    symbol_parser.set_defaults(func=lambda args: print_missing_symbols(args.file))

    spreadsheet_parser = subparsers.add_parser(
        "spreadsheet",
        help="Export to Excel Spreadsheet.",
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
        "-f",
        "--in-file",
        default="input.xlsx",
        help="Spreadsheet to read in.",
    )
    spreadsheet_parser.add_argument(
        "-o",
        "--out-file",
        default="output.xlsx",
        help="Spreadsheet to write out.",
    )
    spreadsheet_parser.set_defaults(func=spreadsheet)

    print_distro_parser = subparsers.add_parser(
        "print-distros",
        help="Print current <distro-name, revision> info.",
    )
    print_distro_parser.set_defaults(func=get_distros)

    distro_parser = subparsers.add_parser("add-distro", help="Add a distro to the database.")
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

    return parser.parse_args(args=args)


def main(args: Optional[str] = None) -> None:
    """
    Main entrypoint for CLI
    """

    args = get_cli_options(args)

    logging.basicConfig(
        level={0: logging.WARNING, 1: logging.INFO}.get(args.verbose, logging.DEBUG),
        format="%(asctime)s %(name)-5s %(levelname)-7s %(message)s",
        datefmt="%m-%d %H:%M",
    )

    config.verbose = args.verbose
    config.dry_run = args.dry_run
    config.since = args.since
    config.fetch = not args.no_fetch

    print("Welcome to Commit Analyzer!")
    args.func(args)
    print("Commit Analyzer completed!")


if __name__ == "__main__":
    main()
