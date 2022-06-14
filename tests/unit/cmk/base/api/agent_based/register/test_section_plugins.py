#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import List

import pytest

from cmk.utils.type_defs import ParsedSectionName, SectionName

import cmk.base.api.agent_based.register.section_plugins as section_plugins
from cmk.base.api.agent_based.section_classes import OIDEnd, SNMPDetectSpecification, SNMPTree
from cmk.base.api.agent_based.type_defs import (
    AgentSectionPlugin,
    SNMPSectionPlugin,
    StringByteTable,
    StringTable,
)


def _generator_function():
    yield None


def _parse_dummy(string_table):  # pylint: disable=unused-argument
    return None


@pytest.mark.parametrize(
    "parse_function",
    [
        _generator_function,
        "bar",
        b"foo",
        None,
        ("foo", "bar"),
        42,
    ],
)
def test_validate_parse_function_type(parse_function) -> None:
    with pytest.raises(TypeError):
        section_plugins._validate_parse_function(
            parse_function,
            expected_annotation=(str, "str"),  # irrelevant for test
        )


@pytest.mark.parametrize(
    "parse_function",
    [
        # argument name must be string_table, and string_table only.
        lambda foo: None,
        lambda string_table, foo: None,
        lambda foo, string_table: None,
    ],
)
def test_validate_parse_function_value(parse_function) -> None:
    with pytest.raises(ValueError):
        section_plugins._validate_parse_function(
            parse_function,
            expected_annotation=(str, "str"),  # ignored
        )


def test_validate_parse_function_annotation_string_table() -> None:
    def _parse_function(string_table: List[StringTable]):
        return string_table

    with pytest.raises(TypeError):
        section_plugins._validate_parse_function(
            _parse_function,
            expected_annotation=(StringByteTable, "StringByteTable"),
        )

    section_plugins._validate_parse_function(
        _parse_function,
        expected_annotation=(List[StringTable], "List[StringTable]"),
    )


def test_validate_supersedings_raise_duplicate() -> None:
    supersedes = [
        SectionName("foo"),
        SectionName("bar"),
        SectionName("foo"),
    ]

    with pytest.raises(ValueError, match="duplicate"):
        section_plugins._validate_supersedings(SectionName("jim"), supersedes)


def test_validate_supersedings_raise_self_superseding() -> None:
    with pytest.raises(ValueError, match="cannot supersede myself"):
        section_plugins._validate_supersedings(SectionName("foo"), [SectionName("foo")])


def test_create_agent_section_plugin() -> None:
    plugin = section_plugins.create_agent_section_plugin(
        name="norris",
        parsed_section_name="chuck",
        parse_function=_parse_dummy,
        supersedes=["foo", "bar"],
    )

    assert isinstance(plugin, AgentSectionPlugin)
    assert len(plugin) == 9
    assert plugin.name == SectionName("norris")
    assert plugin.parsed_section_name == ParsedSectionName("chuck")
    assert plugin.parse_function is _parse_dummy
    assert plugin.host_label_function is section_plugins._noop_host_label_function
    assert plugin.host_label_default_parameters is None
    assert plugin.host_label_ruleset_name is None
    assert plugin.host_label_ruleset_type == "merged"
    assert plugin.supersedes == {SectionName("bar"), SectionName("foo")}


def test_create_snmp_section_plugin() -> None:

    trees: List[SNMPTree] = [
        SNMPTree(
            base=".1.2.3",
            oids=[OIDEnd(), "2.3"],
        ),
    ]

    detect = SNMPDetectSpecification(
        [
            [(".1.2.3.4.5", "Foo.*", True)],
        ]
    )

    plugin = section_plugins.create_snmp_section_plugin(
        name="norris",
        parsed_section_name="chuck",
        parse_function=_parse_dummy,
        fetch=trees,
        detect_spec=detect,
        supersedes=["foo", "bar"],
    )

    assert isinstance(plugin, SNMPSectionPlugin)
    assert len(plugin) == 11
    assert plugin.name == SectionName("norris")
    assert plugin.parsed_section_name == ParsedSectionName("chuck")
    assert plugin.parse_function is _parse_dummy
    assert plugin.host_label_function is section_plugins._noop_host_label_function
    assert plugin.host_label_default_parameters is None
    assert plugin.host_label_ruleset_name is None
    assert plugin.host_label_ruleset_type == "merged"
    assert plugin.detect_spec == detect
    assert plugin.trees == trees
    assert plugin.supersedes == {SectionName("bar"), SectionName("foo")}


def test_create_snmp_section_plugin_single_tree() -> None:

    single_tree = SNMPTree(base=".1.2.3", oids=[OIDEnd(), "2.3"])

    plugin = section_plugins.create_snmp_section_plugin(
        name="norris",
        parse_function=lambda string_table: string_table,
        # just one, no list:
        fetch=single_tree,
        detect_spec=SNMPDetectSpecification([[(".1.2.3.4.5", "Foo.*", True)]]),
    )

    assert plugin.trees == [single_tree]
    # the plugin only specified a single tree (not a list),
    # so a wrapper should unpack the argument:
    assert plugin.parse_function([[["A", "B"]]]) == [["A", "B"]]


def test_validate_supersedings_raise_implicit() -> None:
    all_supersedes_invalid = {
        SectionName("foo"): {SectionName("bar")},
        SectionName("bar"): {SectionName("gee")},
    }

    with pytest.raises(
        ValueError,
        match="implicitly supersedes section.*You must add those to the supersedes keyword",
    ):
        section_plugins.validate_section_supersedes(all_supersedes_invalid)

    # add the implicid superseding, then it should be OK:
    all_supersedes_valid = all_supersedes_invalid.copy()
    all_supersedes_valid[SectionName("foo")].add(SectionName("gee"))

    section_plugins.validate_section_supersedes(all_supersedes_valid)


def test_validate_supersedings_raise_cyclic() -> None:
    all_supersedes_cyclic = {
        SectionName("foo"): {SectionName("bar")},
        SectionName("bar"): {SectionName("foo")},
    }

    with pytest.raises(
        ValueError,
        match="implicitly supersedes section.*This leads to a cyclic superseding",
    ):
        section_plugins.validate_section_supersedes(all_supersedes_cyclic)
