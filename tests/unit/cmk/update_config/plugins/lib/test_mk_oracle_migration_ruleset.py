#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

import pytest

from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import Rule, RuleConditions, RuleOptions, Ruleset
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import Rulespec
from cmk.update_config.plugins.lib.mk_oracle_migration import migrate_ruleset, MIGRATION_NAMESPACE


@pytest.fixture(name="rulespec")
def fixture_rulespec() -> Rulespec:
    return Rulespec(
        name="dummy_rulespec",
        group=RulespecGroupMonitoringConfigurationVarious,
        title=None,
        valuespec=lambda: Dictionary(elements=[], optional_keys=True),
        match_type="dict",
        item_type=None,
        item_spec=None,
        item_name=None,
        item_help=None,
        is_optional=False,
        is_deprecated=False,
        deprecation_planned=False,
        is_for_services=False,
        is_binary_ruleset=False,
        factory_default={},
        help_func=None,
        doc_references=None,
    )


def _legacy_rule(folder: Folder, ruleset: Ruleset, *, rule_id: str, description: str = "") -> Rule:
    return Rule(
        id_=rule_id,
        folder=folder,
        ruleset=ruleset,
        conditions=RuleConditions(host_folder=folder.name()),
        options=RuleOptions(disabled=False, description=description, comment="", docu_url=""),
        value={},
    )


@pytest.mark.usefixtures("request_context")
def test_skips_already_migrated_rule(rulespec: Rulespec) -> None:
    folder = folder_tree().root_folder()
    legacy_ruleset = Ruleset("agent_config:mk_oracle", rulespec=rulespec)
    legacy_ruleset.append_rule(folder, _legacy_rule(folder, legacy_ruleset, rule_id="legacy-1"))

    unified_ruleset = Ruleset("agent_config:mk_oracle_unified", rulespec=rulespec)
    already_migrated_id = str(uuid.uuid5(MIGRATION_NAMESPACE, "legacy-1"))
    unified_ruleset.append_rule(
        folder, _legacy_rule(folder, unified_ruleset, rule_id=already_migrated_id)
    )

    results, skipped = migrate_ruleset(legacy_ruleset, unified_ruleset, disabled=True)

    assert results == []
    assert skipped == 1


@pytest.mark.usefixtures("request_context")
def test_migrated_rule_id_is_deterministic(rulespec: Rulespec) -> None:
    folder = folder_tree().root_folder()
    legacy_ruleset = Ruleset("agent_config:mk_oracle", rulespec=rulespec)
    legacy_ruleset.append_rule(folder, _legacy_rule(folder, legacy_ruleset, rule_id="legacy-1"))
    unified_ruleset = Ruleset("agent_config:mk_oracle_unified", rulespec=rulespec)

    first_results, _ = migrate_ruleset(legacy_ruleset, unified_ruleset, disabled=True)
    second_results, _ = migrate_ruleset(legacy_ruleset, unified_ruleset, disabled=True)

    assert first_results[0].new_rule.id == second_results[0].new_rule.id


@pytest.mark.usefixtures("request_context")
def test_disabled_flag_is_passed_through_when_true(rulespec: Rulespec) -> None:
    folder = folder_tree().root_folder()
    legacy_ruleset = Ruleset("agent_config:mk_oracle", rulespec=rulespec)
    legacy_ruleset.append_rule(folder, _legacy_rule(folder, legacy_ruleset, rule_id="legacy-1"))
    unified_ruleset = Ruleset("agent_config:mk_oracle_unified", rulespec=rulespec)

    results, _ = migrate_ruleset(legacy_ruleset, unified_ruleset, disabled=True)

    assert results[0].new_rule.rule_options.disabled is True


@pytest.mark.usefixtures("request_context")
def test_disabled_flag_is_passed_through_when_false(rulespec: Rulespec) -> None:
    folder = folder_tree().root_folder()
    legacy_ruleset = Ruleset("agent_config:mk_oracle", rulespec=rulespec)
    legacy_ruleset.append_rule(folder, _legacy_rule(folder, legacy_ruleset, rule_id="legacy-1"))
    unified_ruleset = Ruleset("agent_config:mk_oracle_unified", rulespec=rulespec)

    results, _ = migrate_ruleset(legacy_ruleset, unified_ruleset, disabled=False)

    assert results[0].new_rule.rule_options.disabled is False


@pytest.mark.usefixtures("request_context")
def test_new_rule_description_with_legacy_description(rulespec: Rulespec) -> None:
    folder = folder_tree().root_folder()
    legacy_ruleset = Ruleset("agent_config:mk_oracle", rulespec=rulespec)
    legacy_ruleset.append_rule(
        folder,
        _legacy_rule(folder, legacy_ruleset, rule_id="legacy-1", description="My Oracle rule"),
    )
    unified_ruleset = Ruleset("agent_config:mk_oracle_unified", rulespec=rulespec)

    results, _ = migrate_ruleset(legacy_ruleset, unified_ruleset, disabled=True)

    assert results[0].new_rule.rule_options.description == "(Migrated) My Oracle rule"


@pytest.mark.usefixtures("request_context")
def test_new_rule_description_without_legacy_description(rulespec: Rulespec) -> None:
    folder = folder_tree().root_folder()
    legacy_ruleset = Ruleset("agent_config:mk_oracle", rulespec=rulespec)
    legacy_ruleset.append_rule(folder, _legacy_rule(folder, legacy_ruleset, rule_id="legacy-1"))
    unified_ruleset = Ruleset("agent_config:mk_oracle_unified", rulespec=rulespec)

    results, _ = migrate_ruleset(legacy_ruleset, unified_ruleset, disabled=True)

    assert results[0].new_rule.rule_options.description == "(Migrated)"
