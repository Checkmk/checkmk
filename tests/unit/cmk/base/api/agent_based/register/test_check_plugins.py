#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Any, Dict

import pytest

from cmk.utils.type_defs import CheckPluginName, ParsedSectionName

import cmk.base.api.agent_based.register.check_plugins as check_plugins


def dummy_generator(section):  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


MINIMAL_CREATION_KWARGS: Dict[str, Any] = {
    "name": "norris",
    "service_name": "Norris Device",
    "discovery_function": dummy_generator,
    "check_function": dummy_generator,
}


def dummy_function(section):  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


def dummy_function_i(item, section):  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


def dummy_function_ip(item, params, quark):  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


def dummy_function_ips(item, params, section):  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


def dummy_function_jj(section_jim, section_jill):  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


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
def test_invalid_service_name(string, exc_ty):
    with pytest.raises(exc_ty):
        check_plugins._validate_service_name(CheckPluginName("test"), string)


@pytest.mark.parametrize("string", ["whooop", "foo %s bar"])
def test_valid_service_name(string):
    check_plugins._validate_service_name(CheckPluginName("test"), string)


@pytest.mark.parametrize(
    "service_name, expected",
    [
        ("Foo Bar", False),
        ("Foo %s", True),
    ],
)
def test_requires_item(service_name, expected):
    assert check_plugins._requires_item(service_name) == expected


@pytest.mark.parametrize(
    "sections",
    [
        [],
        "mööp",
    ],
)
def test_create_sections_invalid(sections):
    with pytest.raises((TypeError, ValueError)):
        check_plugins.create_subscribed_sections(sections, None)  # type: ignore[arg-type]


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
def test_create_sections(sections, plugin_name, expected):
    assert check_plugins.create_subscribed_sections(sections, plugin_name) == expected


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
def test_validate_function_args(function, has_item, has_params, sections, raises):
    if raises is None:
        check_plugins.validate_function_arguments(
            type_label="check",
            function=function,
            has_item=has_item,
            default_params={} if has_params else None,
            sections=sections,
        )
        return

    with pytest.raises(raises):
        check_plugins.validate_function_arguments(
            type_label="check",
            function=function,
            has_item=has_item,
            default_params={} if has_params else None,
            sections=sections,
        )


@pytest.mark.parametrize("key", list(MINIMAL_CREATION_KWARGS.keys()))
def test_create_check_plugin_mandatory(key):
    kwargs = {k: v for k, v in MINIMAL_CREATION_KWARGS.items() if k != key}
    with pytest.raises(TypeError):
        _ = check_plugins.create_check_plugin(**kwargs)


def test_create_check_plugin_mgmt_reserved():
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


def test_create_check_plugin():
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


def test_module_attribute(fix_register):
    local_check = fix_register.check_plugins[CheckPluginName("local")]
    assert local_check.module == "local"
