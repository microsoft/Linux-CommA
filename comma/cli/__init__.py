# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
CLI entry point for program
"""

import logging
import sys
from functools import cached_property
from typing import Optional, Sequence

from pydantic import ValidationError
from ruamel.yaml import YAML as R_YAML
from ruamel.yaml import YAMLError

from comma.cli.parser import parse_args
from comma.config import BasicConfig, FullConfig
from comma.database.driver import DatabaseDriver
from comma.database.model import Distros, MonitoringSubjects
from comma.downstream import Downstream
from comma.exceptions import CommaError, CommaPluginError
from comma.upstream import Upstream
from comma.util.spreadsheet import Spreadsheet
from comma.util.symbols import Symbols
from comma.util.tracking import Repo


LOGGER = logging.getLogger("comma.cli")
YAML = R_YAML(typ="safe")


class Session:
    """
    Container for session data to avoid duplicate actions
    """

    def __init__(self, config, database) -> None:
        self.config: FullConfig = config
        self.database: DatabaseDriver = database
        self._tracked_paths = None

    @cached_property
    def repo(self):
        """
        Cached property for default repo lookup
        """

        return self._get_repo(since=self.config.upstream_since)

    def _get_repo(
        self,
        since: Optional[str] = None,
        suffix: Optional[str] = None,
    ) -> Repo:
        """
        Clone or update a repo
        """

        name = self.config.upstream.repo
        if suffix:
            name += f"-{suffix}"
        repo = Repo(
            name, self.config.repos[self.config.upstream.repo], self.config.upstream.reference
        )

        if not repo.exists:
            # No local repo, clone from source
            repo.clone(since)

        # Fetch in case reference isn't the default branch
        repo.fetch(since, self.config.upstream.reference)

        repo.checkout(repo.default_ref)

        return repo

    def run(self, options):
        """
        Handle run subcommand
        """

        if options.dry_run:
            # Populate database from configuration file
            with self.database.get_session() as session:
                if session.query(Distros).first() is None:
                    session.add_all(
                        Distros(distroID=name, repoLink=url)
                        for name, url in self.config.repos.items()
                    )

                if session.query(MonitoringSubjects).first() is None:
                    session.add_all(
                        MonitoringSubjects(distroID=target.repo, revision=target.reference)
                        for target in self.config.downstream
                    )

        if options.print_tracked_paths:
            for path in self.get_tracked_paths():
                print(path)

        if options.upstream:
            LOGGER.info("Begin monitoring upstream")
            Upstream(self).process_commits(options.force_update)
            LOGGER.info("Finishing monitoring upstream")

        if options.downstream:
            LOGGER.info("Begin monitoring downstream")
            Downstream(self).monitor()
            LOGGER.info("Finishing monitoring downstream")

    def symbols(self, options):
        """
        Handle symbols subcommand
        """
        repo = self._get_repo(suffix="sym")

        missing = Symbols(self, repo).get_missing_commits(options.file)
        print("Missing symbols from:")
        for commit in missing:
            print(f"  {commit}")

    def get_tracked_paths(self):
        """
        Get list of files paths to monitor for upstream
        This is based on the configuration and can include specific paths or paths dynamically
        determined via plugins
        """
        if self._tracked_paths is not None:
            return self._tracked_paths

        paths = set()
        for path in self.config.upstream.paths:
            plugin_name = None
            if isinstance(path, dict):
                # Configuration verifies there is only one entry and the name starts with '^'
                plugin_name = next(iter(path))[1:]
            elif path.startswith("^"):
                plugin_name = path[1:]

            if plugin_name is None:
                paths.add(path)
                continue

            plugin = self.config.plugins.paths.get(plugin_name)

            if plugin is None:
                raise CommaPluginError(f"No plugin with the name '{plugin_name}' is loaded")

            paths |= plugin(self, path[f"^{plugin_name}"]).get_paths()

        # Sort and cache results
        self._tracked_paths = tuple(sorted(paths))

        return self._tracked_paths

    def downstream(self, options):
        """
        Handle downstream subcommand
        """

        # Print current targets in database
        if options.action in {"list", None}:
            for remote, reference in self.database.iter_downstream_targets():
                print(f"{remote}\t{reference}")

        # Add downstream target
        if options.action == "add":
            self.database.add_downstream_target(options.name, options.url, options.revision)

        elif options.action == "delete":
            if options.revision:
                self.database.delete_downstream_target(options.name, options.revision)
            else:
                self.database.delete_repo(options.name)

    def spreadsheet(self, options):
        """
        Handle spreadsheet subcommand
        """

        spreadsheet = Spreadsheet(self)

        if options.export_commits:
            spreadsheet.export_commits(options.in_file, options.out_file)
        if options.update_commits:
            spreadsheet.update_commits(options.in_file, options.out_file)

    def __call__(self, options) -> None:
        """
        Runs the specified subcommand
        """

        getattr(self, options.subcommand)(options)


def main(args: Optional[Sequence[str]] = None):
    """
    Main CLI entry point
    """

    options = parse_args(args)

    # Configure logging
    logging.basicConfig(
        level={0: logging.WARNING, 1: logging.INFO}.get(options.verbose, logging.DEBUG),
        format="%(asctime)s %(name)-5s %(levelname)-7s %(message)s",
        datefmt="%m-%d %H:%M:%S",
    )

    # If a full configuration is required, CLI parser would ensure this is set
    if options.config:
        options_values = {
            field: getattr(options, field)
            for field in BasicConfig.__fields__
            if hasattr(options, field)
        }
        try:
            config = FullConfig(**YAML.load(options.config) | options_values)
        except (ValidationError, YAMLError) as e:
            print(f"Unable to validate config file: {options.config}")
            sys.exit(e)

    # Fallback to basic configuration
    else:
        config: BasicConfig = BasicConfig(**vars(options))

    try:
        # Get database object
        database = DatabaseDriver(dry_run=options.dry_run, echo=options.verbose > 2)

        # Create session object and invoke subcommand
        Session(config, database)(options)

    except CommaError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()
