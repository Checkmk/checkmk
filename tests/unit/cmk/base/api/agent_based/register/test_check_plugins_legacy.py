#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import inspect

from pytest import MonkeyPatch

from cmk.utils.type_defs import ParsedSectionName, RuleSetName

from cmk.checkers.checking import CheckPluginName

import cmk.base.api.agent_based.checking_classes as checking_classes
import cmk.base.api.agent_based.register.check_plugins_legacy as check_plugins_legacy
from cmk.base.api.agent_based.checking_classes import Metric, Result
from cmk.base.api.agent_based.register.utils_legacy import CheckInfoElement


def dummy_generator(section):  # pylint: disable=unused-argument
    yield from ()


MINIMAL_CHECK_INFO: CheckInfoElement = {
    "service_description": "Norris Device",
    "inventory_function": dummy_generator,
    "check_function": dummy_generator,
}


def test_create_discovery_function(monkeypatch: MonkeyPatch) -> None:
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
        ]

    new_function = check_plugins_legacy._create_discovery_function(
        "norris",
        {"inventory_function": insane_discovery},
        {"params_string": {"levels": "default"}},
    )

    fixed_params = inspect.signature(new_function).parameters
    assert list(fixed_params) == ["section"]
    assert inspect.isgeneratorfunction(new_function)

    result = list(new_function(["info"]))
    expected: list = [
        checking_classes.Service(item="foo"),
        checking_classes.Service(item="foo", parameters={"levels": "default"}),
        "some string",  # bogus value let through intentionally
    ]
    assert result == expected


def test_create_check_function() -> None:
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


def test_create_check_function_with_empty_summary_in_details() -> None:
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


def test_create_check_function_without_details() -> None:
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
        {},  # factory_settings
        {},  # get_check_context
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


def test_create_check_plugin_from_legacy_with_params() -> None:
    check_info_element = MINIMAL_CHECK_INFO.copy()
    check_info_element["group"] = "norris_rule"
    check_info_element["default_levels_variable"] = "norris_default_levels"

    plugin = check_plugins_legacy.create_check_plugin_from_legacy(
        "norris",
        check_info_element,
        {"norris_default_levels": {"levels": (23, 42)}},
        {},
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
    }
    assert plugin.check_ruleset_name == RuleSetName("norris_rule")
    assert plugin.cluster_check_function is None
