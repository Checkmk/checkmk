#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest import MonkeyPatch

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib import rulespecs
from cmk.gui.watolib.notification_parameter import (
    _registry,
    notification_parameter_registry,
    NotificationParameter,
    register_notification_parameters,
)

expected_plugins = [
    "asciimail",
    "cisco_webex_teams",
    "ilert",
    "jira_issues",
    "mail",
    "mkeventd",
    "msteams",
    "opsgenie_issues",
    "pagerduty",
    "pushover",
    "servicenow",
    "signl4",
    "slack",
    "sms_api",
    "spectrum",
    "victorops",
]


def test_registered_notification_parameters() -> None:
    registered_plugins = sorted(notification_parameter_registry.keys())
    assert registered_plugins == sorted(expected_plugins)


def test_register_legacy_notification_parameters(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _registry, "notification_parameter_registry", _registry.NotificationParameterRegistry()
    )
    rulespec_group_registry = rulespecs.RulespecGroupRegistry()
    monkeypatch.setattr(rulespecs, "rulespec_group_registry", rulespec_group_registry)
    monkeypatch.setattr(
        rulespecs, "rulespec_registry", rulespecs.RulespecRegistry(rulespec_group_registry)
    )

    assert RuleGroup.NotificationParameters("xyz") not in rulespecs.rulespec_registry
    assert "xyz" not in _registry.notification_parameter_registry
    register_notification_parameters(
        "xyz",
        Dictionary(
            help="slosh",
            elements=[],
        ),
    )

    cls = _registry.notification_parameter_registry["xyz"]
    assert isinstance(cls, NotificationParameter)
    assert isinstance(cls.spec(), Dictionary)
    assert cls.spec().help() == "slosh"

    assert RuleGroup.NotificationParameters("xyz") in rulespecs.rulespec_registry
