#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest  # type: ignore[import]

from cmk.base.api import PluginName
import cmk.base.api.agent_based.register.check_plugins as check_plugins


def dummy_generator(section):  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


MINIMAL_CREATION_KWARGS = {
    "name": "norris",
    "service_name": "Norris Device",
    "discovery_function": dummy_generator,
    "check_function": dummy_generator,
    "forbidden_names": []
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


@pytest.mark.parametrize("string, exc_ty", [
    (b"foo", TypeError),
    (8, TypeError),
    (None, TypeError),
    ("Foo %s bar %s", ValueError),
    ("", ValueError),
])
def test_invalid_service_name(string, exc_ty):
    with pytest.raises(exc_ty):
        check_plugins._validate_service_name("", string)


@pytest.mark.parametrize("string", ["whooop", "foo %s bar"])
def test_valid_service_name(string):
    check_plugins._validate_service_name("", string)


@pytest.mark.parametrize("service_name, expected", [
    ("Foo Bar", False),
    ("Foo %s", True),
])
def test_requires_item(service_name, expected):
    assert check_plugins._requires_item(service_name) == expected


@pytest.mark.parametrize("sections", [
    [],
    "mööp",
])
def test_create_sections_invalid(sections):
    with pytest.raises((TypeError, ValueError)):
        check_plugins._create_sections(sections, None)


@pytest.mark.parametrize("sections, plugin_name, expected", [
    (None, PluginName("Foo"), [PluginName("Foo")]),
    (["Jim", "Jill"], None, [PluginName("Jim"), PluginName("Jill")]),
])
def test_create_sections(sections, plugin_name, expected):
    assert check_plugins._create_sections(sections, plugin_name) == expected


@pytest.mark.parametrize("function, has_item, has_params, sections, raises", [
    (dummy_function, False, False, [PluginName("name")], None),
    (dummy_function, False, True, [PluginName("name")], TypeError),
    (dummy_function, True, False, [PluginName("name")], TypeError),
    (dummy_function, True, True, [PluginName("name")], TypeError),
    (dummy_function_i, False, False, [PluginName("name")], TypeError),
    (dummy_function_i, False, True, [PluginName("name")], TypeError),
    (dummy_function_i, True, False, [PluginName("name")], None),
    (dummy_function_i, True, True, [PluginName("name")], TypeError),
    (dummy_function_ip, False, False, [PluginName("name")], TypeError),
    (dummy_function_ip, False, True, [PluginName("name")], TypeError),
    (dummy_function_ip, True, False, [PluginName("name")], TypeError),
    (dummy_function_ip, True, True, [PluginName("name")], TypeError),
    (dummy_function_ips, False, False, [PluginName("name")], TypeError),
    (dummy_function_ips, False, True, [PluginName("name")], TypeError),
    (dummy_function_ips, True, False, [PluginName("name")], TypeError),
    (dummy_function_ips, True, True, [PluginName("name")], None),
    (dummy_function_jj, False, False, [PluginName("name")], TypeError),
    (dummy_function_jj, False, False, [PluginName("jill"), PluginName("jim")], TypeError),
    (dummy_function_jj, False, False, [PluginName("jim"), PluginName("jill")], None),
])
def test_validate_function_args(function, has_item, has_params, sections, raises):
    if raises is None:
        check_plugins._validate_function_args("", "", function, has_item, has_params, sections)
        return

    with pytest.raises(raises):
        check_plugins._validate_function_args("", "", function, has_item, has_params, sections)


@pytest.mark.parametrize("key", MINIMAL_CREATION_KWARGS.keys())
def test_create_check_plugin_mandatory(key):
    kwargs = {k: v for k, v in MINIMAL_CREATION_KWARGS.items() if k != key}
    with pytest.raises(TypeError):
        _ = check_plugins.create_check_plugin(**kwargs)


def test_create_check_plugin():
    plugin = check_plugins.create_check_plugin(**MINIMAL_CREATION_KWARGS)

    assert plugin.name == PluginName(MINIMAL_CREATION_KWARGS["name"])
    assert plugin.sections == [PluginName(MINIMAL_CREATION_KWARGS["name"])]
    assert plugin.service_name == MINIMAL_CREATION_KWARGS["service_name"]
    assert plugin.management_board is None
    assert plugin.discovery_function is MINIMAL_CREATION_KWARGS["discovery_function"]
    assert plugin.discovery_default_parameters is None
    assert plugin.discovery_ruleset_name is None
    assert plugin.check_function is MINIMAL_CREATION_KWARGS["check_function"]
    assert plugin.check_default_parameters is None
    assert plugin.check_ruleset_name is None
    assert plugin.cluster_check_function is None
