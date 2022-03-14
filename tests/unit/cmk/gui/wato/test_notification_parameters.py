#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.plugins.wato.utils as utils

# Triggers plugin loading of plugins.wato which registers all the plugins
import cmk.gui.wato
import cmk.gui.watolib.rulespecs as rulespecs
from cmk.gui.valuespec import Dictionary

expected_plugins = [
    "asciimail",
    "cisco_webex_teams",
    "ilert",
    "jira_issues",
    "mail",
    "mkeventd",
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


def test_registered_notification_parameters():
    registered_plugins = sorted(utils.notification_parameter_registry.keys())
    assert registered_plugins == sorted(expected_plugins)


def test_register_legacy_notification_parameters(monkeypatch):
    monkeypatch.setattr(
        utils, "notification_parameter_registry", utils.NotificationParameterRegistry()
    )
    rulespec_group_registry = rulespecs.RulespecGroupRegistry()
    monkeypatch.setattr(rulespecs, "rulespec_group_registry", rulespec_group_registry)
    monkeypatch.setattr(
        rulespecs, "rulespec_registry", rulespecs.RulespecRegistry(rulespec_group_registry)
    )

    assert "notification_parameters:xyz" not in rulespecs.rulespec_registry
    assert "xyz" not in utils.notification_parameter_registry
    cmk.gui.wato.register_notification_parameters(
        "xyz",
        Dictionary(
            help="slosh",
            elements=[],
        ),
    )

    cls = utils.notification_parameter_registry["xyz"]
    assert isinstance(cls.spec, Dictionary)
    assert cls.spec.help() == "slosh"

    assert "notification_parameters:xyz" in rulespecs.rulespec_registry
