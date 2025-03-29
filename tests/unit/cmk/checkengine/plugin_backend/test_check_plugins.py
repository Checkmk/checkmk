#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable
from typing import Any

import pytest

from cmk.checkengine.plugin_backend import check_plugins
from cmk.checkengine.plugin_backend.utils import (
    create_subscribed_sections,
    validate_function_arguments,
)
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckPlugin,
    CheckPluginName,
    InventoryPluginName,
)
from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.discover_plugins import PluginLocation


def dummy_generator(section):
    return
    yield


MINIMAL_CREATION_KWARGS: dict[str, Any] = {
    "name": "norris",
    "service_name": "Norris Device",
    "discovery_function": dummy_generator,
    "check_function": dummy_generator,
    "location": PluginLocation("", ""),
}


def dummy_function(section):
    return
    yield


def dummy_function_i(item, section):
    return
    yield


def dummy_function_ip(item, params, quark):
    return
    yield


def dummy_function_ips(item, params, section):
    return
    yield


def dummy_function_jj(section_jim, section_jill):
    return
    yield


@pytest.mark.parametrize(
    "string, exc_ty",
    [
        (b"foo", TypeError),
        (8, TypeError),
        (None, TypeError),
        ("Foo %s bar %s", ValueError),
        ("", ValueError),
    ],
)
def test_invalid_service_name(string: str, exc_ty: type["TypeError"] | type["ValueError"]) -> None:
    with pytest.raises(exc_ty):
        check_plugins._validate_service_name(CheckPluginName("test"), string)


@pytest.mark.parametrize("string", ["whooop", "foo %s bar"])
def test_valid_service_name(string: str) -> None:
    check_plugins._validate_service_name(CheckPluginName("test"), string)


@pytest.mark.parametrize(
    "service_name, expected",
    [
        ("Foo Bar", False),
        ("Foo %s", True),
    ],
)
def test_requires_item(service_name: str, expected: bool) -> None:
    assert check_plugins._requires_item(service_name) == expected


@pytest.mark.parametrize(
    "sections",
    [
        [],
        "mööp",
    ],
)
def test_create_sections_invalid(sections: list[str] | None) -> None:
    with pytest.raises((TypeError, ValueError)):
        create_subscribed_sections(sections, None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "sections, plugin_name, expected",
    [
        (None, CheckPluginName("Foo"), [ParsedSectionName("Foo")]),
        (
            ["Jim", "Jill"],
            None,
            [ParsedSectionName("Jim"), ParsedSectionName("Jill")],
        ),
    ],
)
def test_create_sections(
    sections: list[str] | None,
    plugin_name: InventoryPluginName | CheckPluginName,
    expected: list[ParsedSectionName],
) -> None:
    assert create_subscribed_sections(sections, plugin_name) == expected


@pytest.mark.parametrize(
    "function, has_item, has_params, sections, raises",
    [
        (dummy_function, False, False, [CheckPluginName("name")], None),
        (dummy_function, False, True, [CheckPluginName("name")], TypeError),
        (dummy_function, True, False, [CheckPluginName("name")], TypeError),
        (dummy_function, True, True, [CheckPluginName("name")], TypeError),
        (dummy_function_i, False, False, [CheckPluginName("name")], TypeError),
        (dummy_function_i, False, True, [CheckPluginName("name")], TypeError),
        (dummy_function_i, True, False, [CheckPluginName("name")], None),
        (dummy_function_i, True, True, [CheckPluginName("name")], TypeError),
        (dummy_function_ip, False, False, [CheckPluginName("name")], TypeError),
        (dummy_function_ip, False, True, [CheckPluginName("name")], TypeError),
        (dummy_function_ip, True, False, [CheckPluginName("name")], TypeError),
        (dummy_function_ip, True, True, [CheckPluginName("name")], TypeError),
        (dummy_function_ips, False, False, [CheckPluginName("name")], TypeError),
        (dummy_function_ips, False, True, [CheckPluginName("name")], TypeError),
        (dummy_function_ips, True, False, [CheckPluginName("name")], TypeError),
        (dummy_function_ips, True, True, [CheckPluginName("name")], None),
        (dummy_function_jj, False, False, [CheckPluginName("name")], TypeError),
        (
            dummy_function_jj,
            False,
            False,
            [CheckPluginName("jill"), CheckPluginName("jim")],
            TypeError,
        ),
        (dummy_function_jj, False, False, [CheckPluginName("jim"), CheckPluginName("jill")], None),
    ],
)
def test_validate_function_args(
    function: Callable,
    has_item: bool,
    has_params: bool,
    sections: list[ParsedSectionName],
    raises: None | type["TypeError"],
) -> None:
    if raises is None:
        validate_function_arguments(
            type_label="check",
            function=function,
            has_item=has_item,
            default_params={} if has_params else None,
            sections=sections,
        )
        return

    with pytest.raises(raises):
        validate_function_arguments(
            type_label="check",
            function=function,
            has_item=has_item,
            default_params={} if has_params else None,
            sections=sections,
        )


@pytest.mark.parametrize("key", list(MINIMAL_CREATION_KWARGS.keys()))
def test_create_check_plugin_mandatory(key: str) -> None:
    kwargs = {k: v for k, v in MINIMAL_CREATION_KWARGS.items() if k != key}
    with pytest.raises(TypeError):
        _ = check_plugins.create_check_plugin(**kwargs)


def test_create_check_plugin_mgmt_reserved() -> None:
    kwargs = MINIMAL_CREATION_KWARGS.copy()
    kwargs["service_name"] = "Management Interface: "
    with pytest.raises(ValueError):
        _ = check_plugins.create_check_plugin(**kwargs)

    kwargs = MINIMAL_CREATION_KWARGS.copy()
    kwargs["name"] = "mgmt_foo"
    with pytest.raises(ValueError):
        _ = check_plugins.create_check_plugin(**kwargs)

    kwargs = MINIMAL_CREATION_KWARGS.copy()
    kwargs["service_name"] = "Management Interface: "
    kwargs["name"] = "mgmt_foo"
    _ = check_plugins.create_check_plugin(**kwargs)


def test_create_check_plugin() -> None:
    plugin = check_plugins.create_check_plugin(**MINIMAL_CREATION_KWARGS)

    assert plugin.name == CheckPluginName(MINIMAL_CREATION_KWARGS["name"])
    assert plugin.sections == [ParsedSectionName(MINIMAL_CREATION_KWARGS["name"])]
    assert plugin.service_name == MINIMAL_CREATION_KWARGS["service_name"]
    assert (
        plugin.discovery_function.__name__ == MINIMAL_CREATION_KWARGS["discovery_function"].__name__
    )
    assert plugin.discovery_default_parameters is None
    assert plugin.discovery_ruleset_name is None
    assert plugin.check_function.__name__ == MINIMAL_CREATION_KWARGS["check_function"].__name__
    assert plugin.check_default_parameters is None
    assert plugin.check_ruleset_name is None


def test_module_attribute(agent_based_plugins: AgentBasedPlugins) -> None:
    local_check = agent_based_plugins.check_plugins[CheckPluginName("local")]
    assert local_check.location == PluginLocation(
        "cmk.plugins.collection.agent_based.local", "check_plugin_local"
    )


TEST_PLUGIN = CheckPlugin(
    CheckPluginName("my_test_plugin"),
    [],
    "Unit Test",
    lambda: [],
    None,
    None,
    "merged",
    lambda: [],
    None,
    None,
    None,
    PluginLocation("not", "relevant"),
)

TEST_PLUGINS = {TEST_PLUGIN.name: TEST_PLUGIN}


def test_get_registered_check_plugins_lookup() -> None:
    assert check_plugins.get_check_plugin(TEST_PLUGIN.name, TEST_PLUGINS) is TEST_PLUGIN


def test_get_registered_check_plugins_no_match() -> None:
    assert (
        check_plugins.get_check_plugin(CheckPluginName("mgmt_this_should_not_exists"), TEST_PLUGINS)
        is None
    )


def test_get_registered_check_plugins_mgmt_factory() -> None:
    mgmt_plugin = check_plugins.get_check_plugin(
        TEST_PLUGIN.name.create_management_name(), TEST_PLUGINS
    )
    assert mgmt_plugin is not None
    assert mgmt_plugin.name.create_basic_name() == TEST_PLUGIN.name
    assert mgmt_plugin.service_name.startswith("Management Interface: ")
