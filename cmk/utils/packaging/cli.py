#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import logging
import sys
from typing import Callable

from cmk.utils import tty

from ._reporter import files_inventory
from ._type_defs import PackageException


def _args_find(
    subparser: argparse.ArgumentParser,
) -> None:
    subparser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include packaged files in report",
    )
    subparser.add_argument(
        "--json",
        action="store_true",
        help="format output as json",
    )


def _command_find(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Show information about local files"""

    files = files_inventory()

    if not args.all:
        files = [f for f in files if not f["package"]]

    if args.json:
        sys.stdout.write(f"{json.dumps(files, indent='  ')}\n")
        return 0

    tty.print_table(
        ["File", "Package", "Version", "Part", "Mode"],
        ["", "", "", "", ""],
        [[f["file"], f["package"], f["version"], f["part_title"], f["mode"]] for f in files],
    )
    return 0


def _parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mkp", description=__doc__)
    parser.add_argument("--debug", "-d", action="store_true")
    subparsers = parser.add_subparsers(required=True)

    _add_command(subparsers, "find", _args_find, _command_find)

    return parser.parse_args(argv)


def _add_command(
    subparsers: argparse._SubParsersAction,
    cmd: str,
    args_adder: Callable[[argparse.ArgumentParser], None],
    handler: Callable[[argparse.Namespace, logging.Logger], int],
) -> None:
    subparser = subparsers.add_parser(cmd, help=handler.__doc__)
    args_adder(subparser)
    subparser.set_defaults(handler=handler)


def main(argv: list[str], logger: logging.Logger) -> int:
    args = _parse_arguments(argv)
    try:
        return args.handler(args, logger)
    except PackageException as exc:
        if args.debug:
            raise
        sys.stderr.write(f"{exc}\n")
        return 1
