#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from logging import getLogger
from typing import Any

import pytest
from pytest_mock import MockerFixture

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName
from cmk.utils.version import Edition, edition

from cmk.gui.valuespec import Dictionary, Float, Migrate
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, RuleConditions, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import Rulespec

from cmk.update_config.plugins.actions import rulesets as rulesets_updater

RuleValue = Any


@pytest.fixture(name="ui_context", autouse=True)
def fixture_ui_context(ui_context: None) -> Iterator[None]:
    yield


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
        is_cloud_and_managed_edition_only=False,
        is_for_services=False,
        is_binary_ruleset=False,
        factory_default={"key": 0},
        help_func=None,
        doc_references=None,
    )


def _instantiate_ruleset(
    ruleset_name: str,
    param_value: RuleValue,
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
    param_value: RuleValue,
    transformed_param_value: RuleValue,
) -> None:
    ruleset = _instantiate_ruleset(
        rulespec_with_migration.name,
        param_value,
        rulespec=rulespec_with_migration,
    )
    rulesets = RulesetCollection({rulespec_with_migration.name: ruleset})

    rulesets_updater._transform_wato_rulesets_params(getLogger(), rulesets)

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
    param_value: RuleValue,
    transformed_param_value: RuleValue,
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
    rulesets_updater._transform_wato_rulesets_params(
        getLogger(),
        all_rulesets,
    )

    assert not all_rulesets.exists(replaced_rulespec.name)

    rules = all_rulesets.get(rulespec_with_migration.name).get_rules()
    assert len(rules) == 1

    rule = rules[0]
    assert len(rule) == 3
    assert rule[2].value == transformed_param_value


@pytest.mark.parametrize(
    ["rulesets", "n_expected_warnings"],
    [
        pytest.param(
            {
                "logwatch_rules": {
                    "reclassify_patterns": [
                        ("C", "\\\\x\\\\y\\\\z", "some comment"),
                        ("W", "\\H", "invalid_regex"),
                    ]
                },
                RuleGroup.CheckgroupParameters("ntp_time"): {
                    "ntp_levels": (10, 200.0, 500.0),
                },
            },
            2,
            id="invalid configuration",
        ),
        pytest.param(
            {
                "logwatch_rules": {
                    "reclassify_patterns": [
                        ("C", "\\\\x\\\\y\\\\z", "some comment"),
                    ]
                },
                RuleGroup.CheckgroupParameters("ntp_time"): {
                    "ntp_levels": (10, 200.0, 500.0),
                },
                **(
                    {}
                    if edition() is Edition.CRE
                    else {RuleGroup.ExtraServiceConf("_sla_config"): "i am skipped"}
                ),
            },
            0,
            id="valid configuration",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_validate_rule_values(
    mocker: MockerFixture,
    rulesets: Mapping[RulesetName, RuleValue],
    n_expected_warnings: int,
) -> None:
    all_rulesets = RulesetCollection(
        {
            ruleset_name: _instantiate_ruleset(
                ruleset_name,
                rule_value,
            )
            for ruleset_name, rule_value in rulesets.items()
        }
    )
    logger = getLogger()
    mock_warner = mocker.patch.object(
        logger,
        "warning",
    )
    rulesets_updater._validate_rule_values(logger, all_rulesets)
    assert mock_warner.call_count == n_expected_warnings


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
    rulesets_updater._transform_remove_null_host_tag_conditions_from_rulesets(getLogger(), rulesets)
    assert ruleset.get_rules()[0][2].get_rule_conditions().host_tags.keys() == expected_keys_after
