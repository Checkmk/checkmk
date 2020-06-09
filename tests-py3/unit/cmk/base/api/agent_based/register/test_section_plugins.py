#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import List

import pytest  # type: ignore[import]

from cmk.lib.snmplib.type_defs import ABCSNMPTree, OIDEnd

import cmk.base.api.agent_based.register.section_plugins as section_plugins
import cmk.base.api.agent_based.section_types as section_types
from cmk.base.api import PluginName


def _generator_function():
    yield None


def _parse_dummy(string_table):  # pylint: disable=unused-argument
    return None


@pytest.mark.parametrize("parse_function", [
    _generator_function,
    "bar",
    b"foo",
    None,
    ("foo", "bar"),
    42,
])
def test_validate_parse_function_type(parse_function):
    with pytest.raises(TypeError):
        section_plugins._validate_parse_function(parse_function)


@pytest.mark.parametrize(
    "parse_function",
    [
        # argument name must be string_table, and string_table only.
        lambda foo: None,
        lambda string_table, foo: None,
        lambda foo, string_table: None,
    ])
def test_validate_parse_function_value(parse_function):
    with pytest.raises(ValueError):
        section_plugins._validate_parse_function(parse_function)


@pytest.mark.parametrize(
    "host_label_function, exception_type",
    [
        (lambda foo: None, TypeError),  # must be a generator
        (_generator_function, ValueError),  # must take section or _section as argument!
    ])
def test_validate_host_label_function_value(host_label_function, exception_type):
    with pytest.raises(exception_type):
        section_plugins._validate_host_label_function(host_label_function)


def test_validate_supersedings():
    supersedes = [
        PluginName("foo"),
        PluginName("bar"),
        PluginName("foo"),
    ]

    with pytest.raises(ValueError, match="duplicate"):
        section_plugins._validate_supersedings(supersedes)


def test_create_agent_section_plugin():
    with pytest.raises(NotImplementedError):
        plugin = section_plugins.create_agent_section_plugin(
            name="norris",
            parsed_section_name="chuck",
            parse_function=_parse_dummy,
            supersedes=None,
            forbidden_names=[],
        )

    with pytest.raises(NotImplementedError):
        plugin = section_plugins.create_agent_section_plugin(
            name="norris",
            parsed_section_name=None,
            parse_function=_parse_dummy,
            supersedes=["Foo", "Bar"],
            forbidden_names=[],
        )

    plugin = section_plugins.create_agent_section_plugin(
        name="norris",
        parsed_section_name=None,  # "chuck"
        parse_function=_parse_dummy,
        supersedes=None,  # ["Foo", "Bar"],
        forbidden_names=[],
    )

    assert isinstance(plugin, section_types.AgentSectionPlugin)
    assert len(plugin) == 5
    assert plugin.name == PluginName("norris")
    assert plugin.parsed_section_name == PluginName("norris")  # "chuck")
    assert plugin.parse_function is _parse_dummy
    assert plugin.host_label_function is section_plugins._noop_host_label_function
    assert plugin.supersedes == []  # [PluginName("Bar"), PluginName("Foo")]


def test_create_snmp_section_plugin():

    trees = [
        section_types.SNMPTree(
            base='.1.2.3',
            oids=[OIDEnd(), '2.3'],
        ),
    ]  # type: List[ABCSNMPTree]

    detect = [
        [('.1.2.3.4.5', 'Foo.*', True)],
    ]

    with pytest.raises(NotImplementedError):
        plugin = section_plugins.create_snmp_section_plugin(
            name="norris",
            parsed_section_name="chuck",
            parse_function=_parse_dummy,
            trees=trees,
            detect_spec=detect,
            supersedes=None,
            forbidden_names=[],
        )

    with pytest.raises(NotImplementedError):
        plugin = section_plugins.create_snmp_section_plugin(
            name="norris",
            parsed_section_name=None,
            parse_function=_parse_dummy,
            trees=trees,
            detect_spec=detect,
            supersedes=["Foo", "Bar"],
            forbidden_names=[],
        )

    plugin = section_plugins.create_snmp_section_plugin(
        name="norris",
        parsed_section_name=None,  # "chuck",
        parse_function=_parse_dummy,
        trees=trees,
        detect_spec=detect,
        supersedes=None,  # ["Foo", "Bar"],
        forbidden_names=[],
    )

    assert isinstance(plugin, section_types.SNMPSectionPlugin)
    assert len(plugin) == 7
    assert plugin.name == PluginName("norris")
    assert plugin.parsed_section_name == PluginName("norris")  # "chuck")
    assert plugin.parse_function is _parse_dummy
    assert plugin.host_label_function is section_plugins._noop_host_label_function
    assert plugin.detect_spec == detect
    assert plugin.trees == trees
    assert plugin.supersedes == []  # [PluginName("Bar"), PluginName("Foo")]
