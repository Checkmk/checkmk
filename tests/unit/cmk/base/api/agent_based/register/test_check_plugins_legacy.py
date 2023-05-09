#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import inspect
from typing import List

from cmk.utils.type_defs import CheckPluginName, ParsedSectionName, RuleSetName

import cmk.base.api.agent_based.checking_classes as checking_classes
import cmk.base.api.agent_based.register.check_plugins_legacy as check_plugins_legacy
import cmk.base.config as config
from cmk.base.api.agent_based.checking_classes import Metric, Result
from cmk.base.check_api import Service as OldService


def dummy_generator(section):  # pylint: disable=unused-argument
    yield from ()


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
            OldService("bar", {"P": "O"}),
        ]

    monkeypatch.setattr(
        config, "_check_contexts", {"norris": {"params_string": {"levels": "default"}}}
    )
    new_function = check_plugins_legacy._create_discovery_function(
        "norris",
        {"inventory_function": insane_discovery},
        config.get_check_context,
    )

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["section"]
    assert inspect.isgeneratorfunction(new_function)

    result = list(new_function(["info"]))
    expected: List = [
        checking_classes.Service(item="foo"),
        checking_classes.Service(item="foo", parameters={"levels": "default"}),
        "some string",  # bogus value let through intentionally
        checking_classes.Service(item="bar", parameters={"P": "O"}),
    ]
    assert result == expected


def test_create_check_function():
    def insane_check(item, _no_params, info):
        assert item == "Test Item"
        assert _no_params == {}
        assert info == ["info"]
        yield 0, "Main info", [("metric1", 23, 2, 3)]
        yield 1, "still main, but very long\nadditional1", [("metric2", 23, None, None, "0", None)]
        yield 2, "additional2\nadditional3", [("metric3", 23, "wtf is this")]
        yield 0, "additional4"
        yield 2, "additional5"
        yield 0, "additional6", [("metric4", 42, r"¯\(o_o)/¯")]
        yield 1, "additional7"

    new_function = check_plugins_legacy._create_check_function(
        "test_plugin",
        {
            "check_function": insane_check,
            "service_description": "Foo %s",
        },
    )

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["item", "params", "section"]
    assert inspect.isgeneratorfunction(new_function)

    results = new_function(item="Test Item", section=["info"], params={})
    # we cannot compare the actual Result objects because of
    # the nasty bypassing of validation in the legacy conversion
    assert list(results) == [
        Result(state=checking_classes.State.OK, summary="Main info", details="Main info"),  # Result
        Metric("metric1", 23.0, levels=(2.0, 3.0), boundaries=(None, None)),  # Metric
        Result(
            state=checking_classes.State.WARN,
            summary="still main, but very long",
            details="still main, but very long\nadditional1\nadditional7",
        ),
        Metric("metric2", 23.0, levels=(None, None), boundaries=(0.0, None)),
        Result(
            state=checking_classes.State.CRIT,
            summary="3 additional details available",
            details="additional2\nadditional3\nadditional5",
        ),
        Metric("metric3", 23.0, levels=(None, None), boundaries=(None, None)),
        Result(
            state=checking_classes.State.OK,
            summary="2 additional details available",
            details="additional4\nadditional6",
        ),
        Metric("metric4", 42.0, levels=(None, None), boundaries=(None, None)),
    ]


def test_create_check_function_with_empty_summary_in_details():
    def insane_check(item, _no_params, info):
        assert item == "Test Item"
        assert _no_params == {}
        assert info == ["info"]
        yield 0, "Main info"
        yield 0, "\nadditional3"

    new_function = check_plugins_legacy._create_check_function(
        "test_plugin",
        {
            "check_function": insane_check,
            "service_description": "Foo %s",
        },
    )

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["item", "params", "section"]
    assert inspect.isgeneratorfunction(new_function)

    results = new_function(item="Test Item", section=["info"], params={})
    # we cannot compare the actual Result objects because of
    # the nasty bypassing of validation in the legacy conversion
    assert list(results) == [
        Result(state=checking_classes.State.OK, summary="Main info", details="Main info"),  # Result
        Result(
            state=checking_classes.State.OK,
            summary="1 additional detail available",
            details="additional3",
        ),
    ]


def test_create_check_function_without_details():
    def insane_check(item, _no_params, info):
        assert item == "Test Item"
        assert _no_params == {}
        assert info == ["info"]
        yield 0, "Main info"

    new_function = check_plugins_legacy._create_check_function(
        "test_plugin",
        {
            "check_function": insane_check,
            "service_description": "Foo %s",
        },
    )

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["item", "params", "section"]
    assert inspect.isgeneratorfunction(new_function)

    results = new_function(item="Test Item", section=["info"], params={})
    # we cannot compare the actual Result objects because of
    # the nasty bypassing of validation in the legacy conversion
    assert list(results) == [
        Result(state=checking_classes.State.OK, summary="Main info", details="Main info"),  # Result
    ]


def test_create_check_function_with_zero_details_after_newline() -> None:
    def insane_check(item, _no_params, info):
        assert item == "Test Item"
        assert _no_params == {}
        assert info == ["info"]
        yield 0, "Main info"
        yield 0, "\n"

    new_function = check_plugins_legacy._create_check_function(
        "test_plugin",
        {
            "check_function": insane_check,
            "service_description": "Foo %s",
        },
    )

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["item", "params", "section"]
    assert inspect.isgeneratorfunction(new_function)

    results = new_function(item="Test Item", section=["info"], params={})
    # we cannot compare the actual Result objects because of
    # the nasty bypassing of validation in the legacy conversion
    assert list(results) == [
        Result(state=checking_classes.State.OK, summary="Main info", details="Main info"),  # Result
    ]


def test_create_check_plugin_from_legacy_wo_params() -> None:

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
    assert plugin.discovery_function.__name__ == "discovery_migration_wrapper"
    assert plugin.discovery_default_parameters is None
    assert plugin.discovery_ruleset_name is None
    assert plugin.check_function.__name__ == "check_migration_wrapper"
    assert plugin.check_default_parameters == {}
    assert plugin.check_ruleset_name is None
    assert plugin.cluster_check_function is None


def test_create_check_plugin_from_legacy_with_params():

    plugin = check_plugins_legacy.create_check_plugin_from_legacy(
        "norris",
        {
            **MINIMAL_CHECK_INFO,
            "group": "norris_rule",
            "default_levels_variable": "norris_default_levels",
        },
        [],
        {"norris_default_levels": {"levels": (23, 42)}},
        lambda _x: {"norris_default_levels": {"levels_lower": (1, 2)}},
    )

    assert plugin.name == CheckPluginName("norris")
    assert plugin.sections == [ParsedSectionName("norris")]
    assert plugin.service_name == MINIMAL_CHECK_INFO["service_description"]
    assert plugin.discovery_function.__name__ == "discovery_migration_wrapper"
    assert plugin.discovery_default_parameters is None
    assert plugin.discovery_ruleset_name is None
    assert plugin.check_function.__name__ == "check_migration_wrapper"
    assert plugin.check_default_parameters == {
        "levels": (23, 42),
        "levels_lower": (1, 2),
    }
    assert plugin.check_ruleset_name == RuleSetName("norris_rule")
    assert plugin.cluster_check_function is None


def test_get_default_params_clean_case():
    # with params
    assert check_plugins_legacy._get_default_parameters(
        check_legacy_info={"default_levels_variable": "foo"},
        factory_settings={"foo": {"levels": (23, 42)}},
        check_context={},
    ) == {"levels": (23, 42)}

    # without params
    assert (
        check_plugins_legacy._get_default_parameters(
            check_legacy_info={},
            factory_settings={},
            check_context={},
        )
        is None
    )


def test_get_default_params_with_user_update():
    # with params
    assert check_plugins_legacy._get_default_parameters(
        check_legacy_info={"default_levels_variable": "foo"},
        factory_settings={"foo": {"levels": (23, 42), "overwrite_this": None}},
        check_context={"foo": {"overwrite_this": 3.14, "more": "is better!"}},
    ) == {
        "levels": (23, 42),
        "overwrite_this": 3.14,
        "more": "is better!",
    }


def test_get_default_params_ignore_user_defined_tuple():
    # with params
    assert (
        check_plugins_legacy._get_default_parameters(
            check_legacy_info={"default_levels_variable": "foo"},
            factory_settings={},
            check_context={"foo": (23, 42)},
        )
        == {}
    )
