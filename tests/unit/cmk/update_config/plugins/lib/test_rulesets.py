#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from logging import getLogger
from typing import Any

import pytest

from cmk.gui.valuespec import Dictionary, Float, Migrate
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, RuleConditions, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import Rulespec

from cmk.update_config.plugins.lib import rulesets as rulesets_updater


@pytest.fixture(name="rulespec_with_migration")
def fixture_rulespec_with_migration() -> Rulespec:
    return Rulespec(
        name="rulespec_with_migration",
        group=RulespecGroupMonitoringConfigurationVarious,
        title=None,
        valuespec=lambda: Migrate(
            valuespec=Dictionary(
                elements=[
                    (
                        "key",
                        Float(),
                    )
                ],
                optional_keys=False,
            ),
            migrate=lambda p: {"key": p["key"] + 1},
        ),
        match_type="dict",
        item_type=None,
        item_spec=None,
        item_name=None,
        item_help=None,
        is_optional=False,
        is_deprecated=False,
        deprecation_planned=False,
        is_cloud_and_managed_edition_only=False,
        is_for_services=False,
        is_binary_ruleset=False,
        factory_default={"key": 0},
        help_func=None,
        doc_references=None,
    )


@pytest.fixture(name="replaced_rulespec")
def fixture_replaced_rulespec() -> Rulespec:
    return Rulespec(
        name="replaced_rulespec",
        group=RulespecGroupMonitoringConfigurationVarious,
        title=None,
        valuespec=lambda: Dictionary(
            elements=[
                (
                    "key",
                    Float(),
                )
            ],
            optional_keys=False,
        ),
        match_type="dict",
        item_type=None,
        item_spec=None,
        item_name=None,
        item_help=None,
        is_optional=False,
        is_deprecated=False,
        deprecation_planned=False,
        is_cloud_and_managed_edition_only=False,
        is_for_services=False,
        is_binary_ruleset=False,
        factory_default={"key": 0},
        help_func=None,
        doc_references=None,
    )


def _instantiate_ruleset(
    ruleset_name: str,
    param_value: object,
    rulespec: Rulespec | None = None,
    conditions: Mapping[str, Any] | None = None,
) -> Ruleset:
    ruleset = Ruleset(ruleset_name, {}, rulespec=rulespec)
    folder = folder_tree().root_folder()
    rule = Rule.from_ruleset_defaults(folder, ruleset)
    rule.value = param_value
    if conditions:
        rule.update_conditions(RuleConditions.from_config(folder.name(), conditions))
    ruleset.append_rule(folder, rule)
    assert ruleset.get_rules()
    return ruleset


@pytest.mark.parametrize(
    ["param_value", "transformed_param_value"],
    [
        pytest.param(
            {"key": 1},
            {"key": 2},
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_transform_wato_rulesets_params(
    rulespec_with_migration: Rulespec,
    param_value: object,
    transformed_param_value: object,
) -> None:
    ruleset = _instantiate_ruleset(
        rulespec_with_migration.name,
        param_value,
        rulespec=rulespec_with_migration,
    )
    rulesets = RulesetCollection({rulespec_with_migration.name: ruleset})

    rulesets_updater.transform_wato_rulesets_params(getLogger(), rulesets)

    assert len(ruleset.get_rules()[0]) == 3
    assert ruleset.get_rules()[0][2].value == transformed_param_value


@pytest.mark.parametrize(
    ["param_value", "transformed_param_value"],
    [
        pytest.param(
            {"key": 1},
            {"key": 2},
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_transform_replaced_wato_rulesets_and_params(
    rulespec_with_migration: Rulespec,
    replaced_rulespec: Rulespec,
    param_value: object,
    transformed_param_value: object,
) -> None:
    all_rulesets = RulesetCollection(
        {
            replaced_rulespec.name: _instantiate_ruleset(
                replaced_rulespec.name,
                param_value,
                rulespec=replaced_rulespec,
            ),
            rulespec_with_migration.name: Ruleset(
                rulespec_with_migration.name,
                {},
                rulespec=rulespec_with_migration,
            ),
        }
    )

    rulesets_updater._transform_replaced_wato_rulesets(
        getLogger(),
        all_rulesets,
        {replaced_rulespec.name: rulespec_with_migration.name},
    )
    rulesets_updater.transform_wato_rulesets_params(
        getLogger(),
        all_rulesets,
    )

    assert not all_rulesets.exists(replaced_rulespec.name)

    rules = all_rulesets.get(rulespec_with_migration.name).get_rules()
    assert len(rules) == 1

    rule = rules[0]
    assert len(rule) == 3
    assert rule[2].value == transformed_param_value


@pytest.mark.usefixtures("request_context")
def test_transform_remove_null_host_tag_conditions_from_rulesets(
    rulespec_with_migration: Rulespec,
) -> None:
    conditions = {
        "host_tags": {
            # good values
            "a": "tag_id",
            "b": {"$ne": "tag_id"},
            "c": {"$or": "tag_id"},
            "d": {"$nor": "tag_id"},
            # bad values
            "e": None,
            "f": {"$ne": None},
            "g": {"$or": None},
            "h": {"$nor": None},
        }
    }
    ruleset = _instantiate_ruleset(
        rulespec_with_migration.name,
        {"key": 1},
        rulespec=rulespec_with_migration,
        conditions=conditions,
    )
    rulesets = RulesetCollection({rulespec_with_migration.name: ruleset})

    expected_keys_before = {"a", "b", "c", "d", "e", "f", "g", "h"}
    expected_keys_after = {"a", "b", "c", "d"}

    assert ruleset.get_rules()[0][2].get_rule_conditions().host_tags.keys() == expected_keys_before
    rulesets_updater.transform_remove_null_host_tag_conditions_from_rulesets(getLogger(), rulesets)
    assert ruleset.get_rules()[0][2].get_rule_conditions().host_tags.keys() == expected_keys_after
