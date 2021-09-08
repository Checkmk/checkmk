#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import alertmanager
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.agent_based_api.v1 import type_defs
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

DATA = [
    [
        """
    {
        "test_alert_group_1": [{
            "name": "test_rule_1",
            "state": "inactive",
            "severity": "warning",
            "message": "foo"
        }, {
            "name": "test_rule_2",
            "state": "pending",
            "severity": "info",
            "message": "bar"
        }, {
            "name": "test_rule_3",
            "state": "firing",
            "severity": "critical",
            "message": "foobar"
        }, {
            "name": "Watchdog",
            "state": "firing",
            "severity": "critical",
            "message": "fööbär"
        }],
        "test_alert_group_2": [{
            "name": "foo",
            "state": "firing",
            "severity": "info",
            "message": "testmessage"
        }]
    }
    """
    ]
]

alternative_discovery_params = alertmanager.DiscoveryParams(
    group_services=(
        False,
        alertmanager.GroupServices(),
    )
)
alternative_check_params = alertmanager.CheckParams()
custom_remapping_check_params = alertmanager.CheckParams(
    alert_remapping=[
        alertmanager.AlertRemapping(
            rule_names=["foo"],
            map={"inactive": 0, "pending": 2, "firing": 1, "none": 1, "n/a": 3},
        ),
    ],
)


@pytest.mark.parametrize(
    "alertmanager_rule_state, params, status",
    [
        (alertmanager.RuleState.INACTIVE, custom_remapping_check_params, state.OK),
        (alertmanager.RuleState.PENDING, custom_remapping_check_params, state.CRIT),
        (alertmanager.RuleState.FIRING, custom_remapping_check_params, state.WARN),
        (alertmanager.RuleState.NONE, custom_remapping_check_params, state.WARN),
        (alertmanager.RuleState.NA, custom_remapping_check_params, state.UNKNOWN),
    ],
)
def test_alertmanager_get_rule_state_remapping(
    alertmanager_rule_state: alertmanager.RuleState,
    params: alertmanager.CheckParams,
    status: state,
):
    rule = alertmanager.Rule(
        rule_name="foo",
        group_name="bar",
        status=alertmanager_rule_state,
        severity=alertmanager.Severity.WARNING,
        message="fööbär",
    )
    assert alertmanager._get_rule_state(rule, params) == status


#   .--Rules---------------------------------------------------------------.
#   |                         ____        _                                |
#   |                        |  _ \ _   _| | ___  ___                      |
#   |                        | |_) | | | | |/ _ \/ __|                     |
#   |                        |  _ <| |_| | |  __/\__ \                     |
#   |                        |_| \_\\__,_|_|\___||___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@pytest.mark.parametrize(
    "params, data, result",
    [
        (
            alertmanager.default_discovery_parameters,
            DATA,
            [
                Service(item="foo"),
            ],
        ),
        (
            alternative_discovery_params,
            DATA,
            [
                Service(item="test_rule_1"),
                Service(item="test_rule_2"),
                Service(item="test_rule_3"),
                Service(item="Watchdog"),
                Service(item="foo"),
            ],
        ),
    ],
)
def test_alertmanager_discover_rules(
    params: alertmanager.DiscoveryParams,
    data: type_defs.StringTable,
    result: DiscoveryResult,
):
    section = alertmanager.parse_alertmanager(data)
    assert list(alertmanager.discovery_alertmanager_rules(params, section)) == result


@pytest.mark.parametrize(
    "item, params, data, result",
    [
        (
            "foo",
            alertmanager.default_check_parameters,
            DATA,
            [
                Result(state=state.OK, summary="Severity: info"),
                Result(state=state.OK, summary="Group name: test_alert_group_2"),
                Result(state=state.CRIT, summary="Active alert", details="testmessage"),
            ],
        ),
        (
            "Watchdog",
            alternative_check_params,
            DATA,
            [
                Result(state=state.OK, summary="Severity: critical"),
                Result(state=state.OK, summary="Group name: test_alert_group_1"),
                Result(state=state.CRIT, summary="Active alert", details="fööbär"),
            ],
        ),
    ],
)
def test_alertmanager_check_rules(
    item: str,
    params: alertmanager.CheckParams,
    data: type_defs.StringTable,
    result: CheckResult,
):
    section = alertmanager.parse_alertmanager(data)
    assert list(alertmanager.check_alertmanager_rules(item, params, section)) == result


#   .--Groups--------------------------------------------------------------.
#   |                      ____                                            |
#   |                     / ___|_ __ ___  _   _ _ __  ___                  |
#   |                    | |  _| '__/ _ \| | | | '_ \/ __|                 |
#   |                    | |_| | | | (_) | |_| | |_) \__ \                 |
#   |                     \____|_|  \___/ \__,_| .__/|___/                 |
#   |                                        |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@pytest.mark.parametrize(
    "params, data, result",
    [
        (
            alertmanager.default_discovery_parameters,
            DATA,
            [
                Service(item="test_alert_group_1"),
            ],
        ),
        (alternative_discovery_params, DATA, []),
    ],
)
def test_alertmanager_discover_groups(
    params: alertmanager.DiscoveryParams,
    data: type_defs.StringTable,
    result: DiscoveryResult,
):
    section = alertmanager.parse_alertmanager(data)
    assert list(alertmanager.discovery_alertmanager_groups(params, section)) == result


@pytest.mark.parametrize(
    "item, params, data, result",
    [
        (
            "test_alert_group_1",
            alertmanager.default_check_parameters,
            DATA,
            [
                Result(state=state.OK, summary="Number of rules: 4"),
                Result(
                    state=state.CRIT,
                    summary="Active alert: test_rule_3",
                    details="test_rule_3: foobar",
                ),
            ],
        )
    ],
)
def test_alertmanager_check_groups(
    item: str,
    params: alertmanager.CheckParams,
    data: type_defs.StringTable,
    result: CheckResult,
):
    section = alertmanager.parse_alertmanager(data)
    assert list(alertmanager.check_alertmanager_groups(item, params, section)) == result


#   .--Summary-------------------------------------------------------------.
#   |            ____                                                      |
#   |           / ___| _   _ _ __ ___  _ __ ___   __ _ _ __ _   _          |
#   |           \___ \| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |         |
#   |            ___) | |_| | | | | | | | | | | | (_| | |  | |_| |         |
#   |           |____/ \__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |         |
#   |                                                       |___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@pytest.mark.parametrize(
    "params, data, result",
    [
        (
            alertmanager.default_discovery_parameters,
            DATA,
            [
                Service(),
            ],
        ),
        (alternative_discovery_params, DATA, []),
    ],
)
def test_alertmanager_discover_summary(
    params: alertmanager.DiscoveryParams,
    data: type_defs.StringTable,
    result: DiscoveryResult,
):
    section = alertmanager.parse_alertmanager(data)
    assert list(alertmanager.discovery_alertmanager_summary(params, section)) == result


@pytest.mark.parametrize(
    "params, data, result",
    [
        (
            alertmanager.default_check_parameters,
            DATA,
            [
                Result(state=state.OK, summary="Number of rules: 5"),
                Result(
                    state=state.CRIT,
                    summary="Active alert: test_rule_3",
                    details="test_rule_3: foobar",
                ),
                Result(state=state.CRIT, summary="Active alert: foo", details="foo: testmessage"),
            ],
        )
    ],
)
def test_alertmanager_check_summary(
    params: alertmanager.CheckParams,
    data: type_defs.StringTable,
    result: CheckResult,
):
    section = alertmanager.parse_alertmanager(data)
    assert list(alertmanager.check_alertmanager_summary(params, section)) == result
