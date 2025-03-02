#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import dataclasses
import sys
from contextlib import contextmanager
from typing import Annotated, Iterator, Literal

import pydantic

from cmk.utils.redis import disable_redis

from cmk.gui.main_modules import load_plugins
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import gen_id
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.http.conflict_options import add_migrate_parsing, Config
from cmk.update_config.http.conflicts import Conflict, detect_conflicts, ForMigration, Migrate
from cmk.update_config.http.migrate import migrate


class Finalize(pydantic.BaseModel):
    command: Literal["finalize"]


class Delete(pydantic.BaseModel):
    command: Literal["delete"]


class Activate(pydantic.BaseModel):
    command: Literal["activate"]


class Deactivate(pydantic.BaseModel):
    command: Literal["deactivate"]


Args = Annotated[
    Migrate | Activate | Deactivate | Delete | Finalize,
    pydantic.Field(discriminator="command"),
]


class ArgsParser(pydantic.RootModel[Args]):
    root: Args


def _new_migrated_rules(config: Config, ruleset_v1: Ruleset, ruleset_v2: Ruleset) -> None:
    for folder, rule_index, rule_v1 in ruleset_v1.get_rules():
        if _migrated_rule(rule_v1.id, ruleset_v2) is None:
            for_migration = detect_conflicts(config, rule_v1.value)
            sys.stdout.write(f"Rule: {folder}, {rule_index}\n")
            if isinstance(for_migration, Conflict):
                sys.stdout.write(f"Can't migrate: {for_migration.type_.value}\n")
                continue
            sys.stdout.write("Migrated, new.\n")
            rule_v2 = _construct_v2_rule(rule_v1, for_migration, ruleset_v2)
            ruleset_v2.append_rule(rule_v1.folder, rule_v2)


def _from_v1(rule_v1_id: str, ruleset_v1: Ruleset) -> Rule | None:
    for _folder, _rule_index, rule_v1 in ruleset_v1.get_rules():
        if rule_v1_id == rule_v1.id:
            return rule_v1
    return None


def _migrated_from(rule_v2: Rule) -> str | None:
    if not rule_v2.rule_options.comment.startswith("Migrated from v1: "):
        return None
    return rule_v2.rule_options.comment.removeprefix("Migrated from v1: ").strip()


def _migrated_rule(rule_v1_id: str, ruleset_v2: Ruleset) -> Rule | None:
    for _folder, _rule_index, rule_v2 in ruleset_v2.get_rules():
        if _migrated_from(rule_v2) == rule_v1_id:
            return rule_v2
    return None


def _construct_v2_rule(rule_v1: Rule, for_migration: ForMigration, ruleset_v2: Ruleset) -> Rule:
    new_rule_value = migrate(for_migration)
    return Rule(
        id_=gen_id(),
        folder=rule_v1.folder,
        ruleset=ruleset_v2,
        conditions=rule_v1.conditions.clone(),
        options=dataclasses.replace(
            rule_v1.rule_options,
            disabled=True,
            comment=f"Migrated from v1: {rule_v1.id}",
        ),
        value=new_rule_value,
        locked_by=None,
    )


def _migrate_main(config: Config, write: bool) -> None:
    with _with_allrulesets() as all_rulesets:
        ruleset_v1 = all_rulesets.get("active_checks:http")
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        _new_migrated_rules(config, ruleset_v1, ruleset_v2)
        if write:
            all_rulesets.save()


def _parse_arguments() -> Args:
    parser = argparse.ArgumentParser(prog="cmk-migrate-http")
    subparser = parser.add_subparsers(dest="command", required=True)

    add_migrate_parsing(subparser.add_parser("migrate", help="Migrate"))

    _parser_activate = subparser.add_parser("activate", help="Activation")

    _parser_activate = subparser.add_parser("delete", help="Delete")

    _parser_deactivate = subparser.add_parser("deactivate", help="Deactivation")

    _parser_finalize = subparser.add_parser("finalize", help="Finalize")

    return ArgsParser.model_validate(vars(parser.parse_args())).root


@contextmanager
def _with_allrulesets() -> Iterator[AllRulesets]:
    load_plugins()
    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        yield AllRulesets.load_all_rulesets()


def _finalize_main() -> None:
    with _with_allrulesets() as all_rulesets:
        ruleset_v1 = all_rulesets.get("active_checks:http")
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        for folder, rule_index, rule_v2 in ruleset_v2.get_rules():
            if (rule_v1_id := _migrated_from(rule_v2)) is not None:
                rule_v1 = _from_v1(rule_v1_id, ruleset_v1)
                if rule_v1 is None:
                    sys.stdout.write(f"Could find counter-part: {folder}, {rule_index}\n")
                    comment = ""
                else:
                    comment = rule_v1.rule_options.comment
                sys.stdout.write("Migrated, edited exiting rule.\n")
                new_rule_v2 = rule_v2.clone(preserve_id=True)
                new_rule_v2.rule_options = dataclasses.replace(
                    rule_v2.rule_options, comment=comment
                )
                ruleset_v2.edit_rule(rule_v2, new_rule_v2)
                if rule_v1 is not None:
                    ruleset_v1.delete_rule(rule_v1)
        all_rulesets.save()


def _delete_main() -> None:
    with _with_allrulesets() as all_rulesets:
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        for folder, rule_index, rule_v2 in ruleset_v2.get_rules():
            if _migrated_from(rule_v2) is not None:
                sys.stdout.write(f"Deleting rule: {folder}, {rule_index}\n")
                ruleset_v2.delete_rule(rule_v2)
        all_rulesets.save()


def _activate_main() -> None:
    with _with_allrulesets() as all_rulesets:
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        for folder, rule_index, rule_v2 in ruleset_v2.get_rules():
            if _migrated_from(rule_v2) is not None:
                sys.stdout.write(f"Activating rule: {folder}, {rule_index}\n")
                new_rule_v2 = rule_v2.clone(preserve_id=True)
                new_rule_v2.rule_options = dataclasses.replace(rule_v2.rule_options, disabled=False)
                ruleset_v2.edit_rule(rule_v2, new_rule_v2)
        all_rulesets.save()


def _deactivate_main() -> None:
    with _with_allrulesets() as all_rulesets:
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        for folder, rule_index, rule_v2 in ruleset_v2.get_rules():
            if _migrated_from(rule_v2) is not None:
                sys.stdout.write(f"Deactivating rule: {folder}, {rule_index}\n")
                new_rule_v2 = rule_v2.clone(preserve_id=True)
                new_rule_v2.rule_options = dataclasses.replace(rule_v2.rule_options, disabled=True)
                ruleset_v2.edit_rule(rule_v2, new_rule_v2)
        all_rulesets.save()


def main() -> None:
    args = _parse_arguments()
    match args:
        case Migrate(write=write):
            _migrate_main(args, write)
        case Activate():
            _activate_main()
        case Deactivate():
            _deactivate_main()
        case Delete():
            _delete_main()
        case Finalize():
            _finalize_main()


if __name__ == "__main__":
    main()
