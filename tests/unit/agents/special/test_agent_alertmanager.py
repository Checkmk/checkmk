#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict

import pytest

from cmk.special_agents import agent_alertmanager

ignore_params = agent_alertmanager.IgnoreAlerts(
    ignore_na=True,
    ignore_alert_rules=["foobar", "test123"],
    ignore_alert_groups=["ignoreme"],
)

DATA = {
    "groups": [
        {
            "name": "test-group-1",
            "rules": [
                {
                    "state": "inactive",
                    "name": "test-rule-1",
                    "labels": {"severity": "info"},
                    "annotations": {"message": "foo"},
                },
                {
                    "state": "firing",
                    "name": "test-rule-2",
                    "labels": {"severity": "warning"},
                    "annotations": {"message": "bar"},
                },
            ],
        },
        {
            "name": "test-group-2",
            "rules": [
                {
                    "name": "test-rule-a",
                    "labels": {"severity": "info"},
                    "annotations": {"message": "foo"},
                },
                {
                    "state": "firing",
                    "name": "test-rule-b",
                    "labels": {"severity": "warning"},
                    "annotations": {"message": "bar"},
                },
            ],
        },
    ]
}
RESULT = {
    "test-group-1": [
        {"name": "test-rule-1", "state": "inactive", "severity": "info", "message": "foo"},
        {"name": "test-rule-2", "state": "firing", "severity": "warning", "message": "bar"},
    ],
    "test-group-2": [
        {"name": "test-rule-b", "state": "firing", "severity": "warning", "message": "bar"}
    ],
}


@pytest.mark.parametrize(
    "data, ignore_alerts, result",
    [
        (DATA, ignore_params, RESULT),
    ],
)
def test_agent_alertmanager_parse(
    data: Dict[str, Any],
    ignore_alerts: agent_alertmanager.IgnoreAlerts,
    result: agent_alertmanager.Groups,
):
    assert agent_alertmanager.parse_rule_data(data["groups"], ignore_alerts) == result


@pytest.mark.parametrize(
    "rule_name, rule_group, rule_state, ignore_alerts, result",
    [
        (
            "foo",
            "bar",
            "inactive",
            ignore_params,
            {"bar": [{"name": "foo", "state": "inactive", "severity": "info", "message": "foo"}]},
        ),
        ("foobar", "bar", "inactive", ignore_params, {"bar": []}),
        ("test123", "bar", "inactive", ignore_params, {"bar": []}),
        ("foo", "bar", None, ignore_params, {"bar": []}),
        ("foo", "ignoreme", "firing", ignore_params, {}),
    ],
)
def test_alertmanager_is_rule_ignored(
    rule_name: str,
    rule_group: str,
    rule_state: str,
    ignore_alerts: agent_alertmanager.IgnoreAlerts,
    result: agent_alertmanager.Groups,
):
    data = {
        "groups": [
            {
                "name": rule_group,
                "rules": [
                    {
                        "state": rule_state,
                        "name": rule_name,
                        "labels": {"severity": "info"},
                        "annotations": {"message": "foo"},
                    }
                ],
            }
        ]
    }
    assert agent_alertmanager.parse_rule_data(data["groups"], ignore_alerts) == result
