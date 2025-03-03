#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import argparse
from typing import Annotated, Literal

import pydantic

from cmk.update_config.https.conflict_options import add_migrate_parsing, Config


class SearchArgs(pydantic.BaseModel):
    host: str | None
    folder: str | None
    folder_recursive: str | None

    def rule_folder(self) -> tuple[str, bool] | None:
        if self.folder is not None:
            return self.folder, False
        if self.folder_recursive is not None:
            return self.folder_recursive, True
        return None


class Migrate(Config, SearchArgs):
    command: Literal["migrate"]
    write: bool = False


class Finalize(SearchArgs):
    command: Literal["finalize"]


class Delete(SearchArgs):
    command: Literal["delete"]


class Activate(SearchArgs):
    command: Literal["activate"]


class Deactivate(SearchArgs):
    command: Literal["deactivate"]


Args = Annotated[
    Migrate | Activate | Deactivate | Delete | Finalize,
    pydantic.Field(discriminator="command"),
]


class _ArgsParser(pydantic.RootModel[Args]):
    root: Args


def _add_search_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--host",
        help="restrict action to rules which have their explicit host condition set up in "
        "such a way that it matches the given host (either by being unset or set)",
    )
    folder_group = parser.add_mutually_exclusive_group()
    folder_group.add_argument(
        "--folder",
        help="restrict action to rules in this folder",
    )
    folder_group.add_argument(
        "--folder-recursive",
        metavar="FOLDER",
        help="restrict action to rules in this folder, or one of its subfolders",
    )
    return parser


def parse_arguments() -> Args:
    parser = argparse.ArgumentParser(prog="cmk-migrate-http")
    subparser = parser.add_subparsers(dest="command", required=True)

    parser_migrate = subparser.add_parser("migrate", help="Migrate")
    _add_search_arguments(parser_migrate)
    add_migrate_parsing(parser_migrate)

    parser_activate = subparser.add_parser("activate", help="Activation")
    _add_search_arguments(parser_activate)

    parser_delete = subparser.add_parser("delete", help="Delete")
    _add_search_arguments(parser_delete)

    parser_deactivate = subparser.add_parser("deactivate", help="Deactivation")
    _add_search_arguments(parser_deactivate)

    parser_finalize = subparser.add_parser("finalize", help="Finalize")
    _add_search_arguments(parser_finalize)

    return _ArgsParser.model_validate(vars(parser.parse_args())).root
