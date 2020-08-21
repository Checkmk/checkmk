#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import inspect

from cmk.utils.type_defs import ParsedSectionName, CheckPluginName, RuleSetName

import cmk.base.api.agent_based.checking_classes as checking_classes
import cmk.base.api.agent_based.register.check_plugins_legacy as check_plugins_legacy
from cmk.base.check_api_utils import Service as OldService
import cmk.base.config as config
from cmk.base.discovered_labels import HostLabel


def dummy_generator(section):  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


MINIMAL_CHECK_INFO = {
    "service_description": "Norris Device",
    "inventory_function": dummy_generator,
    "check_function": dummy_generator,
}


def test_create_discovery_function(monkeypatch):
    def insane_discovery(info):
        """Completely crazy discovery function:

            * wrong arg name
            * is not a generator
            * returns all kinds of stuff
        """
        assert info == ["info"]
        return [
            ("foo", {}),
            ("foo", "params_string"),
            "some string",
            HostLabel("whoop", "deedoo"),
            OldService("bar", {"P": "O"}),
        ]

    monkeypatch.setattr(config, "_check_contexts",
                        {"norris": {
                            "params_string": {
                                "levels": "default"
                            }
                        }})
    new_function = check_plugins_legacy._create_discovery_function(
        "norris",
        {"inventory_function": insane_discovery},
        config.get_check_context,
    )

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["section"]
    assert inspect.isgeneratorfunction(new_function)

    result = list(new_function(["info"]))
    assert result == [
        checking_classes.Service(item="foo"),
        checking_classes.Service(item="foo", parameters={"levels": "default"}),
        "some string",  # bogus value let through intentionally
        checking_classes.Service(item="bar", parameters={"P": "O"}),
    ]


def test_create_check_function():
    def insane_check(item, _no_params, info):
        assert item == "Test Item"
        assert _no_params == {}
        assert info == ["info"]
        yield 0, "Main info", [("mymetric", 23, 2, 3)]
        yield 1, "still main, but very long\nadditional1"
        yield 2, "additional2\nadditional3"

    new_function = check_plugins_legacy._create_check_function(
        "test_plugin",
        {
            "check_function": insane_check,
            "service_description": "Foo %s",
        },
        None,
    )

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["item", "section"]
    assert inspect.isgeneratorfunction(new_function)

    result = new_function(item="Test Item", section=["info"])
    assert list(result) == [
        checking_classes.Result(
            state=checking_classes.state.OK,
            summary="Main info",
        ),
        checking_classes.Metric("mymetric", 23.0, levels=(2.0, 3.0)),
        checking_classes.Result(
            state=checking_classes.state.WARN,
            summary="still main, but very long",
            details="additional1",
        ),
        checking_classes.Result(state=checking_classes.state.CRIT,
                                details="additional2\nadditional3"),
    ]


def test_create_check_plugin_from_legacy_wo_params():

    plugin = check_plugins_legacy.create_check_plugin_from_legacy(
        "norris",
        MINIMAL_CHECK_INFO,
        [],
        {},  # factory_settings
        lambda _x: {},  # get_check_context
    )

    assert plugin.name == CheckPluginName("norris")
    assert plugin.sections == [ParsedSectionName("norris")]
    assert plugin.service_name == MINIMAL_CHECK_INFO["service_description"]
    assert plugin.discovery_function.__name__ == 'discovery_migration_wrapper'
    assert plugin.discovery_default_parameters == {}
    assert plugin.discovery_ruleset_name is None
    assert plugin.check_function.__name__ == 'check_migration_wrapper'
    assert plugin.check_default_parameters == {}
    assert plugin.check_ruleset_name is None
    assert plugin.cluster_check_function.__name__ == "cluster_legacy_mode_from_hell"


def test_create_check_plugin_from_legacy_with_params():

    plugin = check_plugins_legacy.create_check_plugin_from_legacy(
        "norris",
        {
            **MINIMAL_CHECK_INFO,
            "group": "norris_rule",
            "default_levels_variable": "norris_default_levels",
        },
        [],
        {"norris_default_levels": {
            "levels": (23, 42)
        }},
        lambda _x: {"norris_default_levels": {
            "levels_lower": (1, 2)
        }},
    )

    assert plugin.name == CheckPluginName("norris")
    assert plugin.sections == [ParsedSectionName("norris")]
    assert plugin.service_name == MINIMAL_CHECK_INFO["service_description"]
    assert plugin.discovery_function.__name__ == 'discovery_migration_wrapper'
    assert plugin.discovery_default_parameters == {}
    assert plugin.discovery_ruleset_name is None
    assert plugin.check_function.__name__ == 'check_migration_wrapper'
    assert plugin.check_default_parameters == {
        "levels": (23, 42),
        "levels_lower": (1, 2),
    }
    assert plugin.check_ruleset_name == RuleSetName("norris_rule")
    assert plugin.cluster_check_function.__name__ == "cluster_legacy_mode_from_hell"
