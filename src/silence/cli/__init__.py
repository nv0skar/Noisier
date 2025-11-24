from silence.__main__ import CONFIG
from silence.__version__ import __version__

from silence.logging.default_logger import logger
from silence.cli.commands import (
    run,
    createdb,
    new,
    list_templates,
    createapi,
    createtests,
)

from typing import Any, Callable

import argparse
import sys
import sys
import logging


"""Entry point of the Silence's cli"""


def main():
    parser = argparse.ArgumentParser(
        description="Silence: An educational framework for deploying RESTful APIs and Web applications."
    )
    subparsers = parser.add_subparsers(help="Description:", dest="command")

    # Force the user to select one of the available commands,
    # and allow them to provide additional options after it.
    parser.add_argument(
        "-v", "--version", action="version", version=f"Silence v{__version__}"
    )

    parser_list = subparsers.add_parser(
        "list-templates", help="Lists the available project templates"
    )
    parser_list.add_argument(
        "--debug", action="store_true", help="Enables the debug mode"
    )

    parser_new = subparsers.add_parser("new", help="Creates a new project")
    parser_new.add_argument("name", help="The new project's name")
    group = parser_new.add_mutually_exclusive_group()
    group.add_argument(
        "--template", help="Template name to use when creating the new project"
    )
    group.add_argument("--url", help="URL to a Git repo containing a project to clone")
    group.add_argument("--blank", action="store_true", help="Alias to --template blank")
    parser_new.add_argument(
        "--debug", action="store_true", help="Enables the debug mode"
    )

    subparsers.add_parser(
        "createdb",
        help="Runs the provided SQL scripts in the adequate order in the database",
    )
    subparsers.add_parser("run", help="Starts the web server")
    subparsers.add_parser(
        "createapi",
        help="⚠️ DEPRECATED: If specified in the config file, the endpoint generation will occur on each start, a mock file will be written to the '/endpoints/_auto' folder, but no auto generated endpoint will be read from there.",
    )
    subparsers.add_parser(
        "createtests",
        help="Reads the database and generates the main test cases for the entities.",
    )

    # Show the help dialog if the command is issued without any arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # Show silence new's help dialog if it was called without any arguments
    if sys.argv[1].lower() == "new" and len(sys.argv) == 2:
        parser_new.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # If --debug is set, configure the logging level and the global settings
    # This is useful for commands that have no access to a custom config.toml
    # file, such as "new" and "list-templates"
    if "debug" in args and args.debug:
        global _DEBUG
        _DEBUG = True
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    command = args.command.lower()

    def _get_handler() -> Callable[[Any], None]:
        match command:
            case "run":
                return run.handle
            case "createdb":
                return createdb.handle
            case "new":
                return new.handle
            case "list-templates":
                return list_templates.handle
            case "createapi":
                return createapi.handle
            case "createdb":
                return createdb.handle
            case "createtests":
                return createtests.handle
            case _:
                raise ValueError("Bad command!")

    try:
        # Initialize config.toml
        match command:
            case "new" | "list-templates":
                pass
            case _:
                CONFIG.load_config()
        _get_handler()(args)
    except Exception as e:
        logger.error("A fatal error occurred: {}".format(e))
        sys.exit(1)
