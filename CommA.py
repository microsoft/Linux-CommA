#!/usr/bin/env python3
import argparse
import logging

import Util.Config
from DatabaseDriver.DatabaseDriver import DatabaseDriver
from DatabaseDriver.SqlClasses import Distros, MonitoringSubjects
from DownstreamTracker.MonitorDownstream import monitor_downstream
from UpstreamTracker.MonitorUpstream import monitor_upstream
from Util.Symbols import print_missing_symbols

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
        logging.debug(f"Successfully added {args.name} in Distro table")
        s.add(MonitoringSubjects(distroID=args.name, revision=args.revision))
        logging.debug(f"Successfully added {args.name} in MonitoringSubjects table")
    logging.info("Successfully added\tDistro:" + args.name)


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
    help="Repository revision to track. For adding a new branch use distro-name/branch-name format. e.g. SUSE12/SUSE12-SP5-AZURE",
)
distro_parser.set_defaults(func=add_distro)


def add_kernel(args):
    with DatabaseDriver.get_session() as s:
        s.add(MonitoringSubjects(distroID=args.name, revision=args.revision))
    logging.info(
        "Successfully added\t Distro:" + args.name + " revision:" + args.revision
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
    logging.info("Welcome to Commit Analyzer!")
    args.func(args)
    logging.info("Commit Analyzer completed!")
