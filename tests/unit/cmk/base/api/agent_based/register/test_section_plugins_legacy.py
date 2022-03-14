#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest

from cmk.utils.type_defs import ParsedSectionName, SectionName

import cmk.base.api.agent_based.register.section_plugins as section_plugins
import cmk.base.api.agent_based.register.section_plugins_legacy as section_plugins_legacy
from cmk.base.api.agent_based.section_classes import SNMPTree
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.check_api import Service


def old_school_scan_function(oid):
    return oid(".1.2.3.4.5").startswith("norris")


def old_school_parse_function(_info):
    return {"what": "ever"}


def old_school_discover_function(parsed_extra):
    _parsed, _extra_section = parsed_extra
    yield "item1", {"discoverd_param": 42}
    yield Service(
        "item2",
        {},
    )
    yield "item3", "{'how_bad_is_this': 100}"


@pytest.mark.parametrize(
    "name_in, name_out",
    [
        ("foo.bar", "foo"),
        ("foobar", "foobar"),
    ],
)
def test_get_section_name(name_in, name_out):
    assert name_out == section_plugins_legacy.get_section_name(name_in)


def test_create_agent_parse_function():
    compliant_parse_function = section_plugins_legacy._create_agent_parse_function(
        old_school_parse_function
    )

    with pytest.raises(ValueError):
        # raises b/c of wrong signature!
        section_plugins._validate_parse_function(
            old_school_parse_function,
            expected_annotation=(str, "str"),  # irrelevant in test
        )

    section_plugins._validate_parse_function(
        compliant_parse_function,
        expected_annotation=(StringTable, "StringTable"),
    )

    assert old_school_parse_function([]) == compliant_parse_function([])


def test_create_snmp_parse_function():
    compliant_parse_function = section_plugins_legacy._create_snmp_parse_function(
        original_parse_function=old_school_parse_function,
        recover_layout_function=lambda x: x,
        handle_empty_info=False,
    )

    with pytest.raises(ValueError):
        # raises b/c of wrong signature!
        section_plugins._validate_parse_function(
            old_school_parse_function,
            expected_annotation=(str, "str"),  # irrelevant in test
        )

    section_plugins._validate_parse_function(
        compliant_parse_function,
        expected_annotation=(str, "str"),  # irrel. in test, SNMP parse function is not annotated
    )

    arbitrary_non_empty_input = [[["moo"]]]
    assert compliant_parse_function([[]]) is None
    assert compliant_parse_function(
        arbitrary_non_empty_input  # type: ignore[arg-type]
    ) == old_school_parse_function(arbitrary_non_empty_input)


def test_create_snmp_parse_function_handle_empty():
    compliant_parse_function = section_plugins_legacy._create_snmp_parse_function(
        original_parse_function=old_school_parse_function,
        recover_layout_function=lambda x: x,
        handle_empty_info=True,
    )

    assert compliant_parse_function([[]]) == old_school_parse_function([[]])


def test_create_snmp_section_plugin_from_legacy():

    plugin = section_plugins_legacy.create_snmp_section_plugin_from_legacy(
        "norris",
        {
            "parse_function": old_school_parse_function,
            "inventory_function": old_school_discover_function,
        },
        old_school_scan_function,
        (".1.2.3.4.5", ["2", 3]),
        validate_creation_kwargs=True,
    )

    assert plugin.name == SectionName("norris")
    assert plugin.parsed_section_name == ParsedSectionName("norris")
    assert plugin.parse_function.__name__ == "old_school_parse_function"
    assert plugin.host_label_function.__name__ == "_noop_host_label_function"
    assert plugin.supersedes == set()
    assert plugin.detect_spec == [[(".1.2.3.4.5", "norris.*", True)]]
    assert plugin.trees == [SNMPTree(base=".1.2.3.4.5", oids=["2", "3"])]
