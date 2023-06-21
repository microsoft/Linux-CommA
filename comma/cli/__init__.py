# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
CLI entry point for program
"""

import logging
import sys
from typing import Optional, Sequence

from pydantic import ValidationError
from ruamel.yaml import YAML as R_YAML
from ruamel.yaml import YAMLError

from comma.cli.parser import parse_args
from comma.config import BaseConfig, Config
from comma.database.driver import DatabaseDriver
from comma.database.model import Distros, MonitoringSubjects
from comma.downstream import Downstream
from comma.upstream import Upstream
from comma.util.spreadsheet import Spreadsheet
from comma.util.symbols import Symbols
from comma.util.tracking import get_linux_repo


LOGGER = logging.getLogger("comma.cli")
YAML = R_YAML(typ="safe")


def run(options, config, database):
    """
    Handle run subcommand
    """

    if options.dry_run:
        # Populate database from configuration file
        with database.get_session() as session:
            if session.query(Distros).first() is None:
                session.add_all(
                    Distros(distroID=name, repoLink=url) for name, url in config.repos.items()
                )

            if session.query(MonitoringSubjects).first() is None:
                session.add_all(
                    MonitoringSubjects(distroID=target.repo, revision=target.reference)
                    for target in config.downstream
                )

    if options.print_tracked_paths:
        for path in get_linux_repo(config.upstream_since).get_tracked_paths(
            config.upstream.sections
        ):
            print(path)

    if options.upstream:
        LOGGER.info("Begin monitoring upstream")
        Upstream(config, database).process_commits()
        LOGGER.info("Finishing monitoring upstream")

    if options.downstream:
        LOGGER.info("Begin monitoring downstream")
        Downstream(config, database).monitor()
        LOGGER.info("Finishing monitoring downstream")


def main(args: Optional[Sequence[str]] = None):  # pylint: disable=too-many-branches
    """
    Main CLI entry point
    """

    options = parse_args(args)

    # Configure logging
    logging.basicConfig(
        level={0: logging.WARNING, 1: logging.INFO}.get(options.verbose, logging.DEBUG),
        format="%(asctime)s %(name)-5s %(levelname)-7s %(message)s",
        datefmt="%m-%d %H:%M",
    )

    # Start with a basic configuration object
    config: BaseConfig = BaseConfig()

    # If a full configuration is required, CLI parser would ensure this is set
    if options.config:
        try:
            config = Config(**YAML.load(options.config))
        except (ValidationError, YAMLError) as e:
            print(f"Unable to validate config file: {options.config}")
            sys.exit(e)

    # Overwrite some values if they were specified on the command line
    for option in ("downstream_since", "upstream_since"):
        if hasattr(options, option):
            setattr(config, option, getattr(options, option))

    database = DatabaseDriver(dry_run=options.dry_run, echo=options.verbose > 2)

    if options.subcommand == "symbols":
        missing = Symbols(config, database).get_missing_commits(options.file)
        print("Missing symbols from:")
        for commit in missing:
            print(f"  {commit}")

    if options.subcommand == "downstream":
        # Print current targets in database
        if options.action in {"list", None}:
            for remote, reference in database.iter_downstream_targets():
                print(f"{remote}\t{reference}")

        # Add downstream target
        if options.action == "add":
            database.add_downstream_target(options.name, options.url, options.revision)

    if options.subcommand == "run":
        run(options, config, database)

    if options.subcommand == "spreadsheet":
        spreadsheet = Spreadsheet(config, database)
        if args.export_commits:
            spreadsheet.export_commits(args.in_file, args.out_file)
        if args.update_commits:
            spreadsheet.update_commits(args.in_file, args.out_file)


if __name__ == "__main__":
    main()
