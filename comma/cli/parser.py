# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Command line parsers
"""

from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Sequence


DEFAULT_CONFIG = Path("comma.yaml")


def get_base_parsers():
    """
    Options common to parsers
    """

    parsers = {
        "config": ArgumentParser(add_help=False),
        "database": ArgumentParser(add_help=False),
        "logging": ArgumentParser(add_help=False),
        "repo": ArgumentParser(add_help=False),
    }

    parsers["config"].add_argument(
        "-c",
        "--config",
        metavar="FILEPATH",
        type=Path,
        help="Path to configuration file. Defaults to comma.yaml in current directory",
    )

    parsers["database"].add_argument(
        "--dry-run",
        action="store_true",
        help="Do not connect to production database",
    )

    parsers["logging"].add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output verbosity",
    )

    parsers["repo"].add_argument(
        "-U",
        "--upstream-since",
        metavar="APPROXIDATE",
        help="Passed to underlying git commands. By default, the history is not limited",
    )

    return parsers


BASE_PARSERS = get_base_parsers()


def get_run_parser():
    """
    Generate parser for run subcommand
    """

    parser = ArgumentParser(
        "run", description="Analyze commits in Linux repos", parents=BASE_PARSERS.values()
    )

    parser.add_argument(
        "-u", "--upstream", action="store_true", help="Monitor the upstream patches"
    )
    parser.add_argument(
        "-d",
        "--downstream",
        action="store_true",
        help="Monitor the downstream patches",
    )
    parser.add_argument(
        "-p",
        "--print-tracked-paths",
        action="store_true",
        help="Print the paths that would be analyzed",
    )
    parser.add_argument(
        "-D",
        "--downstream-since",
        metavar="APPROXIDATE",
        help="Passed to underlying git commands. By default, the history is not limited",
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update to existing upstream patch records",
    )

    return parser


def get_spreadsheet_parser():
    """
    Generate parser for spreadsheet subcommand
    """

    parser = ArgumentParser(
        "spreadsheet", description="Export to Excel spreadsheet", parents=BASE_PARSERS.values()
    )
    parser.add_argument(
        "-e",
        "--export-commits",
        action="store_true",
        help="Export commits from database into spreadsheet.",
    )
    parser.add_argument(
        "-u",
        "--update-commits",
        action="store_true",
        help="Export downstream distro statuses from database into spreadsheet.",
    )
    parser.add_argument(
        "-f",
        "--in-file",
        default="input.xlsx",
        help="Spreadsheet to read in.",
    )
    parser.add_argument(
        "-o",
        "--out-file",
        default="output.xlsx",
        help="Spreadsheet to write out.",
    )

    return parser


def get_symbol_parser():
    """
    Generate parser for symbol subcommand
    """

    parser = ArgumentParser(
        "symbols",
        description="Compare symbols against patches",
        parents=[BASE_PARSERS["config"], BASE_PARSERS["database"], BASE_PARSERS["logging"]],
    )
    parser.add_argument(
        "file",
        type=Path,
        default="symbols.txt",
        metavar="SYMBOL_FILE",
        help="File with symbols to compare against",
    )

    return parser


def get_downstream_parser():
    """
    Generate parser for downstream subcommand
    """

    parser = ArgumentParser(
        "distro",
        description="List or modify downstream references",
        parents=[BASE_PARSERS["config"], BASE_PARSERS["database"], BASE_PARSERS["logging"]],
    )
    actions = parser.add_mutually_exclusive_group()

    actions.add_argument(
        "-a",
        "--add",
        action="store_const",
        const="add",
        dest="action",
        help="Add downstream target",
    )

    actions.add_argument(
        "-D",
        "--delete",
        action="store_const",
        const="delete",
        dest="action",
        help="Delete downstream target, must specify name, revision optional",
    )

    actions.add_argument(
        "-l",
        "--list",
        action="store_const",
        const="list",
        dest="action",
        help="List downstream targets",
    )

    parser.add_argument(
        "-n",
        "--name",
        help="Database name for repo, (ex: Ubuntu18.04)",
    )
    parser.add_argument(
        "-u",
        "--url",
        help="Repository URL. Required for add if repo in not in database",
    )
    parser.add_argument(
        "-r",
        "--revision",
        help="Repository revision to track",
    )

    return parser


SUBPARSERS = {
    "run": get_run_parser,
    "symbols": get_symbol_parser,
    "spreadsheet": get_spreadsheet_parser,
    "downstream": get_downstream_parser,
}


def parse_args(args: Optional[Sequence[str]] = None):
    """
    Parse command line arguments
    """

    parser = ArgumentParser(description="Commit Analyzer")
    subparsers = parser.add_subparsers(title="subcommands", required=True, dest="subcommand")

    # Populate subparsers
    for name, func in SUBPARSERS.items():
        subparser = func()
        subparsers.add_parser(
            name, parents=[subparser], conflict_handler="resolve", help=subparser.description
        )

    # Check for required options
    options = parser.parse_args(args)

    if options.subcommand == "downstream":
        if options.action == "add" and None in (options.name, options.revision):
            parser.error("Name and revision are required")
        elif options.action == "delete" and options.name is None:
            parser.error("Name is required")

    # Configuration file was specified
    if options.config is not None:
        if not options.config.is_file():
            parser.error(f"Specified configuration file {options.config} does not exist")

    # Default configuration file found
    elif DEFAULT_CONFIG.is_file():
        options.config = DEFAULT_CONFIG

    # Configuration file required, but not specified and default does not exist
    elif options.subcommand in {"run", "spreadsheet", "symbols"}:
        parser.error(
            f"No value for configuration file specified and {DEFAULT_CONFIG} is not present in the current directory"
        )

    return options
