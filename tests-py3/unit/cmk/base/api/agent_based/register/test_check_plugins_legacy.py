#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import inspect

import pytest  # type: ignore[import]

from cmk.utils.type_defs import PluginName

import cmk.base.api.agent_based.checking_types as checking_types
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
        "norris", {"inventory_function": insane_discovery})

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["section"]
    assert inspect.isgeneratorfunction(new_function)

    result = list(new_function(["info"]))
    assert result == [
        checking_types.Service(item="foo"),
        checking_types.Service(item="foo", parameters={"levels": "default"}),
        "some string",  # bogus value let through intentionally
        checking_types.Service(item="bar", parameters={"P": "O"}),
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
        checking_types.Result(
            state=checking_types.state.OK,
            summary="Main info",
        ),
        checking_types.Metric("mymetric", 23.0, levels=(2.0, 3.0)),
        checking_types.Result(
            state=checking_types.state.WARN,
            summary="still main, but very long",
            details="additional1",
        ),
        checking_types.Result(state=checking_types.state.CRIT, details="additional2\nadditional3"),
    ]


def test_create_check_plugin_from_legacy_wo_params(monkeypatch):
    monkeypatch.setattr(config, '_check_contexts', {"norris": {}})

    plugin = check_plugins_legacy.create_check_plugin_from_legacy(
        "norris",
        MINIMAL_CHECK_INFO,
        [],
    )

    assert plugin.name == PluginName("norris")
    assert plugin.sections == [PluginName("norris")]
    assert plugin.service_name == MINIMAL_CHECK_INFO["service_description"]
    assert plugin.discovery_function.__name__ == 'discovery_migration_wrapper'
    assert plugin.discovery_default_parameters is None
    assert plugin.discovery_ruleset_name is None
    assert plugin.check_function.__name__ == 'check_migration_wrapper'
    assert plugin.check_default_parameters is None
    assert plugin.check_ruleset_name is None
    assert plugin.cluster_check_function.__name__ == "cluster_legacy_mode_from_hell"


def test_create_check_plugin_from_legacy_with_params(monkeypatch):
    monkeypatch.setattr(config, 'factory_settings', {"norris_default_levels": {"levels": (23, 42)}})
    monkeypatch.setattr(config, '_check_contexts',
                        {"norris": {
                            "norris_default_levels": {
                                "levels_lower": (1, 2)
                            }
                        }})

    plugin = check_plugins_legacy.create_check_plugin_from_legacy(
        "norris",
        {
            **MINIMAL_CHECK_INFO,
            "group": "norris_rule",
            "default_levels_variable": "norris_default_levels",
        },
        [],
    )

    assert plugin.name == PluginName("norris")
    assert plugin.sections == [PluginName("norris")]
    assert plugin.service_name == MINIMAL_CHECK_INFO["service_description"]
    assert plugin.discovery_function.__name__ == 'discovery_migration_wrapper'
    assert plugin.discovery_default_parameters is None
    assert plugin.discovery_ruleset_name is None
    assert plugin.check_function.__name__ == 'check_migration_wrapper'
    assert plugin.check_default_parameters == {
        "levels": (23, 42),
        "levels_lower": (1, 2),
    }
    assert plugin.check_ruleset_name == PluginName("norris_rule")
    assert plugin.cluster_check_function.__name__ == "cluster_legacy_mode_from_hell"


@pytest.mark.parametrize("params", [
    "foo_levels",
    (1, 2),
])
def test_un_wrap_parameters(params):
    wrapped = check_plugins_legacy.wrap_parameters(params)
    assert isinstance(wrapped, dict)
    assert check_plugins_legacy.unwrap_parameters(wrapped) is params
