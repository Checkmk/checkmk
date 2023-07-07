#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from logging import getLogger
from typing import Any

import pytest
from pytest_mock import MockerFixture

from cmk.utils.rulesets.ruleset_matcher import RulesetName
from cmk.utils.version import edition, Edition

from cmk.checkengine.checking import CheckPluginName

import cmk.gui.watolib.timeperiods as timeperiods
from cmk.gui.valuespec import Dictionary, Float, Migrate
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
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
        is_cloud_edition_only=False,
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
        is_cloud_edition_only=False,
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
) -> Ruleset:
    ruleset = Ruleset(ruleset_name, {}, rulespec=rulespec)
    folder = folder_tree().root_folder()
    rule = Rule.from_ruleset_defaults(folder, ruleset)
    rule.value = param_value
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


@pytest.mark.usefixtures("request_context")
def test_remove_removed_check_plugins_from_ignored_checks() -> None:
    ruleset = Ruleset("ignored_checks", {})
    ruleset.replace_folder_config(
        folder_tree().root_folder(),
        [
            {
                "id": "1",
                "condition": {},
                "options": {"disabled": False},
                "value": ["a", "b", "mgmt_c"],
            },
            {
                "id": "2",
                "condition": {},
                "options": {"disabled": False},
                "value": ["d", "e"],
            },
            {
                "id": "3",
                "condition": {},
                "options": {"disabled": False},
                "value": ["mgmt_f"],
            },
            {
                "id": "4",
                "condition": {},
                "options": {"disabled": False},
                "value": ["a", "g"],
            },
        ],
    )
    rulesets = RulesetCollection({"ignored_checks": ruleset})
    rulesets_updater._remove_removed_check_plugins_from_ignored_checks(
        rulesets,
        {
            CheckPluginName("b"),
            CheckPluginName("d"),
            CheckPluginName("e"),
            CheckPluginName("f"),
        },
    )
    leftover_rules = [rule for (_folder, idx, rule) in rulesets.get("ignored_checks").get_rules()]
    assert len(leftover_rules) == 2
    assert leftover_rules[0].id == "1"
    assert leftover_rules[1].id == "4"
    assert leftover_rules[0].value == ["a", "mgmt_c"]
    assert leftover_rules[1].value == ["a", "g"]


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
                "checkgroup_parameters:ntp_time": {
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
                "checkgroup_parameters:ntp_time": {
                    "ntp_levels": (10, 200.0, 500.0),
                },
                **(
                    {}
                    if edition() is Edition.CRE
                    else {"extra_service_conf:_sla_config": "i am skipped"}
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


def test_transform_time_range() -> None:
    time_range = ((8, 0), (16, 0))
    assert rulesets_updater._transform_time_range(time_range) == ("08:00", "16:00")


def test_get_timeperiod_name() -> None:
    time_range = [((8, 0), (16, 0)), ((17, 0), (20, 0))]
    assert rulesets_updater._get_timeperiod_name(time_range) == "timeofday_0800-1600_1700-2000"


@pytest.mark.usefixtures("request_context")
def test_create_timeperiod() -> None:
    time_range = [((8, 0), (16, 0)), ((17, 0), (20, 0))]
    rulesets_updater._create_timeperiod("timeofday_0800-1600_1700-2000", time_range)

    timeperiod = timeperiods.load_timeperiods()["timeofday_0800-1600_1700-2000"]
    assert timeperiod == {
        "alias": "Created by migration of timeofday parameter (08:00-16:00, 17:00-20:00)",
        "monday": [("08:00", "16:00"), ("17:00", "20:00")],
        "tuesday": [("08:00", "16:00"), ("17:00", "20:00")],
        "wednesday": [("08:00", "16:00"), ("17:00", "20:00")],
        "thursday": [("08:00", "16:00"), ("17:00", "20:00")],
        "friday": [("08:00", "16:00"), ("17:00", "20:00")],
        "saturday": [("08:00", "16:00"), ("17:00", "20:00")],
        "sunday": [("08:00", "16:00"), ("17:00", "20:00")],
    }


@pytest.mark.parametrize(
    "old_param_value, transformed_param_value",
    [
        pytest.param(
            {"timeofday": [((8, 0), (16, 0)), ((17, 0), (20, 0))], "minage": (2, 1)},
            {
                "tp_default_value": {},
                "tp_values": [("timeofday_0800-1600_1700-2000", {"minage": (2, 1)})],
            },
            id="without_timeperiods",
        ),
        pytest.param(
            {
                "tp_default_value": {"timeofday": [((8, 0), (16, 0))], "minage": (2, 1)},
                "tp_values": [("24x7", {"maxage": (200, 1000)})],
            },
            {
                "tp_default_value": {},
                "tp_values": [("timeofday_0800-1600", {"minage": (2, 1)})],
            },
            id="timeofday_in_default_timeperiod",
        ),
        pytest.param(
            {
                "tp_default_value": {"minage": (2, 1)},
                "tp_values": [("24x7", {"timeofday": [((8, 0), (16, 0))], "minage": (2, 1)})],
            },
            {
                "tp_default_value": {"minage": (2, 1)},
                "tp_values": [("24x7", {"minage": (2, 1)})],
            },
            id="timeofday_in_nondefault_timeperiod",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_transform_fileinfo_timeofday_to_timeperiods_fileinfo_ruleset(
    old_param_value: RuleValue,
    transformed_param_value: RuleValue,
) -> None:
    fileinfo_ruleset = _instantiate_ruleset("checkgroup_parameters:fileinfo", old_param_value)
    empty_ruleset = Ruleset("checkgroup_parameters:fileinfo-groups", {})

    rulesets = RulesetCollection(
        {
            "checkgroup_parameters:fileinfo": fileinfo_ruleset,
            "checkgroup_parameters:fileinfo-groups": empty_ruleset,
        }
    )

    rulesets_updater._transform_fileinfo_timeofday_to_timeperiods(rulesets)

    ruleset = rulesets.get_rulesets()["checkgroup_parameters:fileinfo"]
    assert ruleset.get_rules()[0][2].value == transformed_param_value


@pytest.mark.parametrize(
    "old_param_value, transformed_param_value",
    [
        pytest.param(
            {"timeofday": [((8, 0), (16, 0)), ((17, 0), (20, 0))], "minage": (2, 1)},
            {
                "tp_default_value": {},
                "tp_values": [("timeofday_0800-1600_1700-2000", {"minage": (2, 1)})],
            },
            id="without_timeperiods",
        ),
        pytest.param(
            {
                "tp_default_value": {"timeofday": [((8, 0), (16, 0))], "minage": (2, 1)},
                "tp_values": [("24x7", {"maxage": (200, 1000)})],
            },
            {
                "tp_default_value": {},
                "tp_values": [("timeofday_0800-1600", {"minage": (2, 1)})],
            },
            id="timeofday_in_default_timeperiod",
        ),
        pytest.param(
            {
                "tp_default_value": {"minage": (2, 1)},
                "tp_values": [("24x7", {"timeofday": [((8, 0), (16, 0))], "minage": (2, 1)})],
            },
            {
                "tp_default_value": {"minage": (2, 1)},
                "tp_values": [("24x7", {"minage": (2, 1)})],
            },
            id="timeofday_in_nondefault_timeperiod",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_transform_fileinfo_timeofday_to_timeperiods_fileinfo_groups_ruleset(
    old_param_value: RuleValue,
    transformed_param_value: RuleValue,
) -> None:
    empty_ruleset = Ruleset("checkgroup_parameters:fileinfo", {})
    fileinfo_group_ruleset = _instantiate_ruleset(
        "checkgroup_parameters:fileinfo-groups", old_param_value
    )
    rulesets = RulesetCollection(
        {
            "checkgroup_parameters:fileinfo": empty_ruleset,
            "checkgroup_parameters:fileinfo-groups": fileinfo_group_ruleset,
        }
    )

    rulesets_updater._transform_fileinfo_timeofday_to_timeperiods(rulesets)

    ruleset = rulesets.get_rulesets()["checkgroup_parameters:fileinfo-groups"]
    assert ruleset.get_rules()[0][2].value == transformed_param_value
