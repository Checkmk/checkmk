#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

import omdlib


class _Shared(BaseModel, frozen=True):
    site: str
    verbose: bool


class Restore(_Shared):
    command: Literal["restore"] = "restore"
    old_site: str
    reuse: bool


type Finalize = Annotated[Restore, Field(discriminator="command")]


def args_to_command_line(args: Finalize, version: str = omdlib.__version__) -> list[str]:
    cmd_line = [f"/omd/versions/{version}/lib/omd/omd_site_user"]
    cmd_line.extend([args.command, "--site", args.site])
    if args.verbose:
        cmd_line.append("--verbose")
    match args:
        case Restore():
            cmd_line.extend(["--old-site", args.old_site])
            if args.reuse:
                cmd_line.append("--reuse")
    return cmd_line


class _ArgsParser(RootModel[Finalize]):
    root: Finalize


def parse_arguments(sysv: Sequence[str] | None = None) -> Finalize:
    parser = argparse.ArgumentParser(description="Run `omd` code as site user.")
    subparser = parser.add_subparsers(
        dest="command",
        required=True,
        help="Internal tool used by `omd`. The command-line API is subject to change.",
    )

    shared_parser = argparse.ArgumentParser(add_help=False)
    shared_parser.add_argument("--site", required=True, help="The target site")
    shared_parser.add_argument("--verbose", action="store_true", help="Provide debug information")

    parser_restore = subparser.add_parser(
        "restore",
        parents=[shared_parser],
        help="Finalize site restore.",
    )
    parser_restore.add_argument(
        "--old-site",
        required=True,
        help="The previous name of the site",
    )
    parser_restore.add_argument(
        "--reuse",
        default=False,
        action="store_true",
        help="Whether to reuse previous site",
    )

    args = parser.parse_args(sysv)
    return _ArgsParser.model_validate(vars(args)).root
