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
        help="Restrict action to rules which have their explicit host condition set up in such a way that it matches the given host (either by being unset or set)",
    )
    folder_group = parser.add_mutually_exclusive_group()
    folder_group.add_argument(
        "--folder",
        help="Restrict action to rules in this folder",
    )
    folder_group.add_argument(
        "--folder-recursive",
        metavar="FOLDER",
        help="Restrict action to rules in this folder, or one of its subfolders",
    )
    return parser


def parse_arguments() -> Args:
    parser = argparse.ArgumentParser(prog="cmk-migrate-http")
    subparser = parser.add_subparsers(
        dest="command",
        required=True,
        description="Migrate HTTP Web Service v1 rules to the new v2 rule set. Start by calling ‘cmk-migrate-http migrate -h’ to understand the migration logic. After creating the rules, activate them using the script to see them in monitoring. Activated rules can also be deactivated or deleted using the script. Only finalize the rules as the last step. After finalizing the rules, no more actions can be performed on these rules using the script.",
    )

    parser_migrate = subparser.add_parser(
        "migrate",
        help="Migrate v1 rules to v2, only performs a dry run by default",
        description="Iterate on existing v1 rules and attempt to create a matching v2 rule. Start with a dry run to determine which v1 rules will cause incompatibilities/conflicts that need to be skipped or resolved. Proceed to resolve conflicts by specifying the desired option in the command. Once you are satisfied with the output of the dry run, use the --write option to create the rules.",
    )
    _add_search_arguments(parser_migrate)
    add_migrate_parsing(parser_migrate)

    parser_activate = subparser.add_parser(
        "activate",
        help="Activate v2 rules created by the script and have not been finalized",
        description="Deactivate v2 rules created by the script that have not been finalized. Use before finalizing as the script cannot deactivate rules that have already been finalized.",
    )
    _add_search_arguments(parser_activate)

    parser_delete = subparser.add_parser(
        "delete",
        help="Delete v2 rules that have not been yet finalized",
        description="Delete v2 rules created by the script that have not been finalized. Use before finalizing as the script cannot deactivate rules that have already been finalized.",
    )
    _add_search_arguments(parser_delete)

    parser_deactivate = subparser.add_parser(
        "deactivate",
        help="Deactivate v2 rules that have not been finalized",
        description="Deactivate v2 rules created by the script that have not been finalized. Use before finalizing as the script cannot deactivate rules that have already been finalized.",
    )
    _add_search_arguments(parser_deactivate)

    parser_finalize = subparser.add_parser(
        "finalize",
        help="Delete migrated v1 rules and remove their references front the v2 counterparts, this can not be undone",
        description="Delete v1 rules that have been migrated and remove the migration references from the created v2 rules. Use only as the final step of the process, as the script can not take any action on finalized rules. This can not be undone.",
    )
    _add_search_arguments(parser_finalize)

    return _ArgsParser.model_validate(vars(parser.parse_args())).root
