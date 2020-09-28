#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from testlib.base import Scenario

from cmk.utils.log import logger
from cmk.utils.type_defs import SectionName
import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.type_defs import ABCSNMPBackend, OID_END, OIDBytes, OIDEnd, SNMPHostConfig, SNMPTree

import cmk.base.config as config
from cmk.base.api.agent_based.register.section_plugins_legacy import _create_snmp_trees
from cmk.base.check_api import BINARY

SNMPConfig = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname="testhost",
    ipaddress="1.2.3.4",
    credentials="",
    port=42,
    is_bulkwalk_host=False,
    is_snmpv2or3_without_bulkwalk_host=False,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits=[],
    snmpv3_contexts=[],
    character_encoding="ascii",
    is_usewalk_host=False,
    is_inline_snmp_host=False,
    record_stats=False,
)


class SNMPTestBackend(ABCSNMPBackend):
    def get(self, oid, context_name=None):
        pass

    def walk(self, oid, check_plugin_name=None, table_base_oid=None, context_name=None):
        return [("%s.%s" % (oid, r), b"C0FEFE") for r in (1, 2, 3)]


@pytest.mark.parametrize("column", snmp_table.SPECIAL_COLUMNS)
def test_value_encoding(column):
    assert snmp_table._value_encoding(column) == "string"


@pytest.mark.parametrize("snmp_info, expected_values", [
    (
        SNMPTree(
            base='.1.3.6.1.4.1.13595.2.2.3.1',
            oids=[
                OIDEnd(),
                OIDBytes("16"),
            ],
        ),
        [
            ['1', [67, 48, 70, 69, 70, 69]],
            ['2', [67, 48, 70, 69, 70, 69]],
            ['3', [67, 48, 70, 69, 70, 69]],
        ],
    ),
])
def test_get_snmp_table(monkeypatch, snmp_info, expected_values):
    def get_all_snmp_tables(info):
        backend = SNMPTestBackend(SNMPConfig, logger)
        if not isinstance(info, list):
            return snmp_table.get_snmp_table(SectionName("unit_test"), info, backend=backend)
        return [
            snmp_table.get_snmp_table(SectionName("unit_test"), i, backend=backend) for i in info
        ]

    assert get_all_snmp_tables(snmp_info) == expected_values


@pytest.mark.parametrize(
    "encoding,columns,expected",
    [
        (None, [([b'\xc3\xbc'], "string")], [[u"ü"]]),  # utf-8
        (None, [([b'\xc3\xbc'], "binary")], [[[195, 188]]]),  # utf-8
        (None, [([b"\xfc"], "string")], [[u"ü"]]),  # latin-1
        (None, [([b'\xfc'], "binary")], [[[252]]]),  # latin-1
        ("utf-8", [([b'\xc3\xbc'], "string")], [[u"ü"]]),
        ("latin1", [([b'\xfc'], "string")], [[u"ü"]]),
        ("cp437", [([b'\x81'], "string")], [[u"ü"]]),
    ])
def test_sanitize_snmp_encoding(monkeypatch, encoding, columns, expected):
    ts = Scenario().add_host("localhost")
    ts.set_ruleset("snmp_character_encodings", [
        (encoding, [], config.ALL_HOSTS, {}),
    ])
    config_cache = ts.apply(monkeypatch)

    snmp_config = config_cache.get_host_config("localhost").snmp_config("")
    assert snmp_table._sanitize_snmp_encoding(columns, snmp_config) == expected


def test_is_bulkwalk_host(monkeypatch):
    ts = Scenario().set_ruleset("bulkwalk_hosts", [
        ([], ["localhost"], {}),
    ])
    ts.add_host("abc")
    ts.add_host("localhost")
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config("abc").snmp_config("").is_bulkwalk_host is False
    assert config_cache.get_host_config("localhost").snmp_config("").is_bulkwalk_host is True
