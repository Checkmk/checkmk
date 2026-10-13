#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pytest import MonkeyPatch

from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib import rulespecs
from cmk.gui.watolib.notification_parameter import (
    _registry,
    NotificationParameter,
    register_notification_parameters,
)
from cmk.ruleset_matcher.definition import RuleGroup


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


@pytest.mark.usefixtures("request_context")
def test_legacy_proxy_url_is_migrated_to_the_structured_proxy() -> None:
    visitor = get_visitor(
        _registry.notification_parameter_registry.form_spec("slack"),
        VisitorOptions(migrate_values=True, mask_values=False),
    )

    disk_value = visitor.to_disk(
        RawDiskData(
            {
                "general": {"description": "slack", "comment": "", "docu_url": ""},
                "parameter_properties": {
                    "webhook_url": ("webhook_url", "https://hooks.slack.com/services/x"),
                    "proxy_url": ("cmk_postprocessed", "explicit_proxy", "http://proxy.lan:3128"),
                },
            }
        )
    )

    assert isinstance(disk_value, dict)
    assert disk_value["parameter_properties"]["proxy_url"] == (
        "cmk_postprocessed",
        "explicit_proxy",
        {"scheme": "http", "proxy_server_name": "proxy.lan", "port": 3128},
    )
