#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest  # type: ignore[import]

from cmk.utils.type_defs import ParsedSectionName, SectionName
from cmk.snmplib.type_defs import SNMPTree

import cmk.base.api.agent_based.register.section_plugins_legacy as section_plugins_legacy
import cmk.base.api.agent_based.register.section_plugins as section_plugins
from cmk.base.api.agent_based.type_defs import AgentStringTable
from cmk.base.check_api_utils import Service
from cmk.base.discovered_labels import DiscoveredHostLabels, HostLabel


def old_school_scan_function(oid):
    return oid(".1.2.3.4.5").startswith("norris")


def old_school_parse_function(_info):
    return {"what": "ever"}


HOST_LABELS = [
    HostLabel("foo", "bar"),
    HostLabel("gee", "boo"),
    HostLabel("heinz", "hirn"),
]


def old_school_discover_function(parsed_extra):
    _parsed, _extra_section = parsed_extra
    yield "item1", {"discoverd_param": 42}
    yield HOST_LABELS[0]
    yield Service(
        "item2",
        {},
        host_labels=DiscoveredHostLabels(*HOST_LABELS[1:]),
    )
    yield "item3", "{'how_bad_is_this': 100}"


@pytest.mark.parametrize("name_in, name_out", [
    ("foo.bar", "foo"),
    ("foobar", "foobar"),
])
def test_get_section_name(name_in, name_out):
    assert name_out == section_plugins_legacy.get_section_name(name_in)


def test_create_agent_parse_function():
    compliant_parse_function = section_plugins_legacy._create_agent_parse_function(
        old_school_parse_function)

    with pytest.raises(ValueError):
        # raises b/c of wrong signature!
        section_plugins._validate_parse_function(
            old_school_parse_function,
            expected_annotation=(str, "str"),  # irrelevant in test
        )

    section_plugins._validate_parse_function(
        compliant_parse_function,
        expected_annotation=(AgentStringTable, "AgentStringTable"),
    )

    assert old_school_parse_function([]) == compliant_parse_function([])


def test_create_snmp_parse_function():
    compliant_parse_function = section_plugins_legacy._create_snmp_parse_function(
        old_school_parse_function, lambda x: x)

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

    assert old_school_parse_function([]) == compliant_parse_function([])


@pytest.mark.parametrize("disco_func, labels_expected", [
    (old_school_discover_function, HOST_LABELS),
    (lambda x: None, []),
    (lambda x: [], []),
])
def test_create_host_label_function(disco_func, labels_expected):
    host_label_function = section_plugins_legacy._create_host_label_function(
        disco_func, ["some_extra_section"])

    assert host_label_function is not None
    section_plugins.validate_function_arguments(
        type_label="host_label",
        function=host_label_function,
        has_item=False,
        default_params=None,
        sections=[ParsedSectionName("__only_one_seciton__")],
    )

    # check that we can pass an un-unpackable argument now!
    actual_labels = list(host_label_function({"parse": "result"}))

    assert actual_labels == labels_expected


def test_create_snmp_section_plugin_from_legacy():

    plugin = section_plugins_legacy.create_snmp_section_plugin_from_legacy(
        "norris",
        {
            'parse_function': old_school_parse_function,
            'inventory_function': old_school_discover_function,
        },
        old_school_scan_function,
        (".1.2.3.4.5", ["2", 3]),
    )

    assert plugin.name == SectionName("norris")
    assert plugin.parsed_section_name == ParsedSectionName("norris")
    assert plugin.parse_function.__name__ == "old_school_parse_function"
    assert plugin.host_label_function.__name__ == "host_label_function"
    assert plugin.supersedes == set()
    assert plugin.detect_spec == [[(".1.2.3.4.5", "norris.*", True)]]
    assert plugin.trees == [SNMPTree(base=".1.2.3.4.5", oids=["2", "3"])]
