#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import argparse
import io
import sys
from pathlib import Path
from typing import Mapping

import pytest
from pytest_mock import MockerFixture

# This GUI specific fixture is also needed in this context
from tests.unit.cmk.gui.conftest import load_plugins  # noqa: F401 # pylint: disable=unused-import

import cmk.utils.log
import cmk.utils.paths
from cmk.utils.type_defs import CheckPluginName, RulesetName, RuleValue
from cmk.utils.version import is_raw_edition

import cmk.gui.config
import cmk.gui.watolib.timeperiods as timeperiods
from cmk.gui.valuespec import Dictionary, Float, Transform
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import Rulespec

import cmk.update_config.legacy as update_config


@pytest.fixture(name="uc")
def fixture_uc() -> update_config.UpdateConfig:
    return update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def test_parse_arguments_defaults() -> None:
    assert update_config.parse_arguments([]).__dict__ == {
        "debug": False,
        "verbose": 0,
    }


def test_parse_arguments_verbose() -> None:
    assert update_config.parse_arguments(["-v"]).verbose == 1
    assert update_config.parse_arguments(["-v"] * 2).verbose == 2
    assert update_config.parse_arguments(["-v"] * 3).verbose == 3


def test_parse_arguments_debug() -> None:
    assert update_config.parse_arguments(["--debug"]).debug is True


def test_update_config_init() -> None:
    update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def mock_run() -> int:
    sys.stdout.write("XYZ\n")
    return 0


def test_main(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    monkeypatch.setattr(update_config.UpdateConfig, "run", lambda self: mock_run())
    assert update_config.main([]) == 0
    assert "XYZ" in buf.getvalue()


def test_cleanup_version_specific_caches_missing_directory(uc: update_config.UpdateConfig) -> None:
    uc._cleanup_version_specific_caches()


def test_cleanup_version_specific_caches(uc: update_config.UpdateConfig) -> None:
    paths = [
        Path(cmk.utils.paths.include_cache_dir, "builtin"),
        Path(cmk.utils.paths.include_cache_dir, "local"),
        Path(cmk.utils.paths.precompiled_checks_dir, "builtin"),
        Path(cmk.utils.paths.precompiled_checks_dir, "local"),
    ]
    for base_dir in paths:
        base_dir.mkdir(parents=True, exist_ok=True)
        cached_file = base_dir / "if"
        with cached_file.open("w", encoding="utf-8") as f:
            f.write("\n")
        uc._cleanup_version_specific_caches()
        assert not cached_file.exists()
        assert base_dir.exists()


@pytest.fixture(name="rulespec_with_transform")
def fixture_rulespec_with_transform() -> Rulespec:
    return Rulespec(
        name="rulespec_with_transform",
        group=RulespecGroupMonitoringConfigurationVarious,
        title=None,
        valuespec=lambda: Transform(
            Dictionary(
                elements=[
                    (
                        "key",
                        Float(),
                    )
                ],
                optional_keys=False,
            ),
            forth=lambda p: {"key": p["key"] + 1},
        ),
        match_type="dict",
        item_type=None,
        item_spec=None,
        item_name=None,
        item_help=None,
        is_optional=False,
        is_deprecated=False,
        is_for_services=False,
        is_binary_ruleset=False,
        factory_default={"key": 0},
        help_func=None,
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
        is_for_services=False,
        is_binary_ruleset=False,
        factory_default={"key": 0},
        help_func=None,
    )


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
def test__transform_wato_rulesets_params(
    uc: update_config.UpdateConfig,
    rulespec_with_transform: Rulespec,
    param_value: RuleValue,
    transformed_param_value: RuleValue,
) -> None:
    ruleset = _instantiate_ruleset(
        rulespec_with_transform.name,
        param_value,
        rulespec=rulespec_with_transform,
    )
    rulesets = RulesetCollection()
    rulesets.set_rulesets({rulespec_with_transform.name: ruleset})

    uc._transform_wato_rulesets_params(rulesets)

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
def test__transform_replaced_wato_rulesets_and_params(
    uc: update_config.UpdateConfig,
    rulespec_with_transform: Rulespec,
    replaced_rulespec: Rulespec,
    param_value: RuleValue,
    transformed_param_value: RuleValue,
) -> None:
    all_rulesets = RulesetCollection()
    all_rulesets.set_rulesets(
        {
            replaced_rulespec.name: _instantiate_ruleset(
                replaced_rulespec.name,
                param_value,
                rulespec=replaced_rulespec,
            ),
            rulespec_with_transform.name: Ruleset(
                rulespec_with_transform.name,
                {},
                rulespec=rulespec_with_transform,
            ),
        }
    )

    uc._transform_replaced_wato_rulesets(
        all_rulesets,
        {replaced_rulespec.name: rulespec_with_transform.name},
    )
    uc._transform_wato_rulesets_params(all_rulesets)

    assert not all_rulesets.exists(replaced_rulespec.name)

    rules = all_rulesets.get(rulespec_with_transform.name).get_rules()
    assert len(rules) == 1

    rule = rules[0]
    assert len(rule) == 3
    assert rule[2].value == transformed_param_value


def _instantiate_ruleset(
    ruleset_name: str,
    param_value: RuleValue,
    rulespec: Rulespec | None = None,
) -> Ruleset:
    ruleset = Ruleset(ruleset_name, {}, rulespec=rulespec)
    rule = Rule.from_ruleset_defaults(Folder(""), ruleset)
    rule.value = param_value
    ruleset.append_rule(Folder(""), rule)
    assert ruleset.get_rules()
    return ruleset


@pytest.mark.usefixtures("request_context")
def test_remove_removed_check_plugins_from_ignored_checks(uc: update_config.UpdateConfig) -> None:
    ruleset = Ruleset("ignored_checks", {})
    ruleset.from_config(
        Folder(""),
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
    rulesets = RulesetCollection()
    rulesets.set_rulesets({"ignored_checks": ruleset})
    uc._remove_removed_check_plugins_from_ignored_checks(
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
                **({} if is_raw_edition() else {"extra_service_conf:_sla_config": "i am skipped"}),
            },
            0,
            id="valid configuration",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_validate_rule_values(
    mocker: MockerFixture,
    uc: update_config.UpdateConfig,
    rulesets: Mapping[RulesetName, RuleValue],
    n_expected_warnings: int,
) -> None:
    all_rulesets = RulesetCollection()
    all_rulesets.set_rulesets(
        {
            ruleset_name: _instantiate_ruleset(
                ruleset_name,
                rule_value,
            )
            for ruleset_name, rule_value in rulesets.items()
        }
    )
    mock_warner = mocker.patch.object(
        uc._logger,
        "warning",
    )
    uc._validate_rule_values(all_rulesets)
    assert mock_warner.call_count == n_expected_warnings


@pytest.fixture(name="old_path")
def fixture_old_path() -> Path:
    return Path(cmk.utils.paths.var_dir, "wato", "log", "audit.log")


@pytest.fixture(name="new_path")
def fixture_new_path() -> Path:
    return Path(cmk.utils.paths.var_dir, "wato", "log", "wato_audit.log")


@pytest.fixture(name="old_audit_log")
def fixture_old_audit_log(old_path: Path) -> Path:
    old_path.parent.mkdir(exist_ok=True, parents=True)
    with old_path.open("w") as f:
        f.write(
            """
1604991356 - cmkadmin liveproxyd-activate Activating changes of Livestatus Proxy configuration
1604991356 - cmkadmin liveproxyd-activate Activating changes of Livestatus Proxy configuration
1604992040 :heute2 cmkadmin create-host Created new host heute2.
1604992159 :heute2 cmkadmin delete-host Deleted host heute2
1604992163 :heute1 cmkadmin create-host Created new host heute1.
1604992166 :heute12 cmkadmin create-host Created new host heute12.
"""
        )
    return old_path


def mock_audit_log_entry(action: str, diff_text: str) -> AuditLogStore.Entry:
    return AuditLogStore.Entry(
        time=0, object_ref=None, user_id="", action=action, text="", diff_text=diff_text
    )


def test__transform_time_range(uc: update_config.UpdateConfig) -> None:
    time_range = ((8, 0), (16, 0))
    assert uc._transform_time_range(time_range) == ("08:00", "16:00")


def test__get_timeperiod_name(uc: update_config.UpdateConfig) -> None:
    time_range = [((8, 0), (16, 0)), ((17, 0), (20, 0))]
    assert uc._get_timeperiod_name(time_range) == "timeofday_0800-1600_1700-2000"


@pytest.mark.usefixtures("request_context")
def test__create_timeperiod(uc: update_config.UpdateConfig) -> None:
    time_range = [((8, 0), (16, 0)), ((17, 0), (20, 0))]
    uc._create_timeperiod("timeofday_0800-1600_1700-2000", time_range)

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
def test__transform_fileinfo_timeofday_to_timeperiods(  # type:ignore[no-untyped-def]
    uc: update_config.UpdateConfig, old_param_value: RuleValue, transformed_param_value: RuleValue
):
    rulesets = RulesetCollection()
    ruleset = _instantiate_ruleset("checkgroup_parameters:fileinfo", old_param_value)
    rulesets.set_rulesets({"checkgroup_parameters:fileinfo": ruleset})

    uc._transform_fileinfo_timeofday_to_timeperiods(rulesets)

    ruleset = rulesets.get_rulesets()["checkgroup_parameters:fileinfo"]
    assert ruleset.get_rules()[0][2].value == transformed_param_value
