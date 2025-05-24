#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import NamedTuple

from cmk.gui.config import active_config
from cmk.gui.utils import gen_id
from cmk.gui.watolib.automations import ENV_VARIABLE_FORCE_CLI_INTERFACE
from cmk.gui.watolib.rulesets import Rule, Ruleset

from cmk.update_config.https.arguments import SearchArgs
from cmk.update_config.https.conflict_options import Config
from cmk.update_config.https.conflicts import Conflict, detect_conflicts, ForMigration
from cmk.update_config.https.migrate import migrate
from cmk.update_config.https.render import (
    MIGRATE_POSTFIX,
    print_summary_activated,
    print_summary_deactivated,
    print_summary_delete,
    print_summary_dryrun,
    print_summary_finalize,
    print_summary_write,
)
from cmk.update_config.https.search import select, with_allrulesets


class _Count(NamedTuple):
    conflicts: int
    rules: int
    skipped: int


def _new_migrated_rules(
    search: SearchArgs, config: Config, ruleset_v1: Ruleset, ruleset_v2: Ruleset
) -> _Count:
    conflict_count = 0
    rule_count = 0
    skip_count = 0
    for folder, rule_index, rule_v1 in select(ruleset_v1, search):
        rule_count += 1
        if rule_v1.rule_options.disabled:
            rule_str = _render_rule(folder.title(), rule_index, rule_v1.value["name"])
            sys.stdout.write(f"{rule_str}\n")
            sys.stdout.write("Rule is disabled, skipping.\n")
            skip_count += 1
        elif _migrated_rule(rule_v1.id, ruleset_v2) is None:
            for_migration = detect_conflicts(config, rule_v1.value)
            rule_str = _render_rule(folder.title(), rule_index, rule_v1.value["name"])
            sys.stdout.write(f"{rule_str}\n")
            if isinstance(for_migration, Conflict):
                conflict_count += 1
                sys.stdout.write(f"Can't migrate: {for_migration.render()}\n")
                continue
            rule_v2 = _construct_v2_rule(rule_v1, for_migration, ruleset_v2)
            index = ruleset_v2.append_rule(rule_v1.folder, rule_v2)
            sys.stdout.write(f"Migrated to v2 rule with index #{index}.\n")
        else:
            skip_count += 1
    return _Count(conflicts=conflict_count, rules=rule_count, skipped=skip_count)


def _service_name_from_v2(rule_v2: Rule) -> str:
    return rule_v2.value["endpoints"][0]["service_name"]["name"].removesuffix(MIGRATE_POSTFIX)  # type: ignore[no-any-return]


def _render_rule(folder_title: str, rule_index: int, service_name: str) -> str:
    return f"Folder: {folder_title}, Rule: #{rule_index} - {service_name}"


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


def migrate_main(search: SearchArgs, config: Config, write: bool) -> None:
    with _force_automations_cli_interface(), with_allrulesets() as all_rulesets:
        ruleset_v1 = all_rulesets.get("active_checks:http")
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        count = _new_migrated_rules(search, config, ruleset_v1, ruleset_v2)
        if write:
            sys.stdout.write("Saving rule sets...\n")
            all_rulesets.save(
                pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )
            print_summary_write(count.conflicts, count.rules, count.skipped)
        else:
            print_summary_dryrun(count.conflicts, count.rules, count.skipped)


def _strip_postfix(value: dict) -> None:
    for endpoint in value["endpoints"]:
        endpoint["service_name"]["name"] = endpoint["service_name"]["name"].removesuffix(
            MIGRATE_POSTFIX
        )


def finalize_main(search: SearchArgs) -> None:
    with _force_automations_cli_interface(), with_allrulesets() as all_rulesets:
        ruleset_v1 = all_rulesets.get("active_checks:http")
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        rulecount_v1 = 0
        rulecount_v2 = 0
        for folder, rule_index, rule_v2 in select(ruleset_v2, search):
            if (rule_v1_id := _migrated_from(rule_v2)) is not None:
                rule_str = _render_rule(folder.title(), rule_index, _service_name_from_v2(rule_v2))
                sys.stdout.write(f"{rule_str}\n")
                rule_v1 = _from_v1(rule_v1_id, ruleset_v1)
                if rule_v1 is None:
                    sys.stdout.write("Could find v1 counter-part.\n")
                    comment = ""
                else:
                    comment = rule_v1.rule_options.comment
                new_rule_v2 = rule_v2.clone(preserve_id=True)
                new_rule_v2.rule_options = dataclasses.replace(
                    rule_v2.rule_options, comment=comment
                )
                _strip_postfix(new_rule_v2.value)
                ruleset_v2.edit_rule(rule_v2, new_rule_v2)
                rulecount_v2 += 1
                if rule_v1 is not None:
                    rulecount_v1 += 1
                    sys.stdout.write(f"Deleted v1 counter-part #{rule_v1.index()}.\n")
                    ruleset_v1.delete_rule(rule_v1)
                sys.stdout.write(f"Finalized v2 rule #{rule_index}.\n")
        print_summary_finalize(rulecount_v1, rulecount_v2)
        if rulecount_v1 or rulecount_v2:
            sys.stdout.write("Saving rule sets...\n")
            all_rulesets.save(
                pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )


def delete_main(search: SearchArgs) -> None:
    with _force_automations_cli_interface(), with_allrulesets() as all_rulesets:
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        count = 0
        for folder, rule_index, rule_v2 in select(ruleset_v2, search):
            if _migrated_from(rule_v2) is not None:
                rule_str = _render_rule(folder.title(), rule_index, _service_name_from_v2(rule_v2))
                sys.stdout.write(f"{rule_str}\n")
                sys.stdout.write("Deleting rule.\n")
                count += 1
                ruleset_v2.delete_rule(rule_v2)
        print_summary_delete(count)
        if count:
            sys.stdout.write("Saving rule sets...\n")
            all_rulesets.save(
                pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )


def activate_main(search: SearchArgs) -> None:
    with _force_automations_cli_interface(), with_allrulesets() as all_rulesets:
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        count = 0
        for folder, rule_index, rule_v2 in select(ruleset_v2, search):
            if _migrated_from(rule_v2) is not None:
                rule_str = _render_rule(folder.title(), rule_index, _service_name_from_v2(rule_v2))
                sys.stdout.write(f"{rule_str}\n")
                if rule_v2.rule_options.disabled:
                    sys.stdout.write("Activating rule.\n")
                    count += 1
                    new_rule_v2 = rule_v2.clone(preserve_id=True)
                    new_rule_v2.rule_options = dataclasses.replace(
                        rule_v2.rule_options, disabled=False
                    )
                    ruleset_v2.edit_rule(rule_v2, new_rule_v2)
                else:
                    sys.stdout.write("Already active.\n")
        print_summary_activated(count)
        if count:
            sys.stdout.write("Saving rulesets...\n")
            all_rulesets.save(
                pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )


def deactivate_main(search: SearchArgs) -> None:
    with _force_automations_cli_interface(), with_allrulesets() as all_rulesets:
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        count = 0
        for folder, rule_index, rule_v2 in select(ruleset_v2, search):
            if _migrated_from(rule_v2) is not None:
                rule_str = _render_rule(folder.title(), rule_index, _service_name_from_v2(rule_v2))
                sys.stdout.write(f"{rule_str}\n")
                if not rule_v2.rule_options.disabled:
                    sys.stdout.write("Deactivating rule.\n")
                    count += 1
                    new_rule_v2 = rule_v2.clone(preserve_id=True)
                    new_rule_v2.rule_options = dataclasses.replace(
                        rule_v2.rule_options, disabled=True
                    )
                    ruleset_v2.edit_rule(rule_v2, new_rule_v2)
                else:
                    sys.stdout.write("Already deactivated.\n")
        print_summary_deactivated(count)
        if count:
            sys.stdout.write("Saving rulesets...\n")
            all_rulesets.save(
                pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )


@contextmanager
def _force_automations_cli_interface() -> Generator[None]:
    try:
        os.environ[ENV_VARIABLE_FORCE_CLI_INTERFACE] = "True"
        yield
    finally:
        os.environ.pop(ENV_VARIABLE_FORCE_CLI_INTERFACE, None)
