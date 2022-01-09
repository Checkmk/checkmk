#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

from cmk.utils.log import logger
from cmk.utils.type_defs import HostName, SectionName

import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.type_defs import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackend,
    SNMPBackendEnum,
    SNMPHostConfig,
    SpecialColumn,
)

import cmk.base.config as config

SNMPConfig = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname=HostName("testhost"),
    ipaddress="1.2.3.4",
    credentials="",
    port=42,
    is_bulkwalk_host=False,
    is_snmpv2or3_without_bulkwalk_host=False,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits={},
    snmpv3_contexts=[],
    character_encoding="ascii",
    is_usewalk_host=False,
    snmp_backend=SNMPBackendEnum.CLASSIC,
)


class SNMPTestBackend(SNMPBackend):
    def get(self, oid, context_name=None):
        pass

    def walk(self, oid, section_name=None, table_base_oid=None, context_name=None):
        return [("%s.%s" % (oid, r), b"C0FEFE") for r in (1, 2, 3)]


@pytest.mark.parametrize(
    "snmp_info, expected_values",
    [
        (
            BackendSNMPTree(
                base=".1.3.6.1.4.1.13595.2.2.3.1",
                oids=[
                    BackendOIDSpec(SpecialColumn.END, "string", False),
                    BackendOIDSpec("16", "binary", False),
                ],
            ),
            [
                ["1", [67, 48, 70, 69, 70, 69]],
                ["2", [67, 48, 70, 69, 70, 69]],
                ["3", [67, 48, 70, 69, 70, 69]],
            ],
        ),
    ],
)
def test_get_snmp_table(monkeypatch, snmp_info, expected_values):
    def get_all_snmp_tables(info):
        backend = SNMPTestBackend(SNMPConfig, logger)
        if not isinstance(info, list):
            return snmp_table.get_snmp_table(
                section_name=SectionName("unit_test"),
                tree=info,
                walk_cache={},
                backend=backend,
            )
        return [
            snmp_table.get_snmp_table(
                section_name=SectionName("unit_test"),
                tree=i,
                walk_cache={},
                backend=backend,
            )
            for i in info
        ]

    assert get_all_snmp_tables(snmp_info) == expected_values


@pytest.mark.parametrize(
    "encoding,columns,expected",
    [
        (None, [([b"\xc3\xbc"], "string")], [["ü"]]),  # utf-8
        (None, [([b"\xc3\xbc"], "binary")], [[[195, 188]]]),  # utf-8
        (None, [([b"\xfc"], "string")], [["ü"]]),  # latin-1
        (None, [([b"\xfc"], "binary")], [[[252]]]),  # latin-1
        ("utf-8", [([b"\xc3\xbc"], "string")], [["ü"]]),
        ("latin1", [([b"\xfc"], "string")], [["ü"]]),
        ("cp437", [([b"\x81"], "string")], [["ü"]]),
    ],
)
def test_sanitize_snmp_encoding(monkeypatch, encoding, columns, expected):
    ts = Scenario()
    ts.add_host("localhost")
    ts.set_ruleset(
        "snmp_character_encodings",
        [
            (encoding, [], config.ALL_HOSTS, {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)

    snmp_config = config_cache.get_host_config("localhost").snmp_config("")
    assert snmp_table._sanitize_snmp_encoding(columns, snmp_config) == expected


def test_is_bulkwalk_host(monkeypatch):
    ts = Scenario()
    ts.set_ruleset(
        "bulkwalk_hosts",
        [
            ([], ["localhost"], {}),
        ],
    )
    ts.add_host("abc")
    ts.add_host("localhost")
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config("abc").snmp_config("").is_bulkwalk_host is False
    assert config_cache.get_host_config("localhost").snmp_config("").is_bulkwalk_host is True


def test_is_classic_at_snmp_v1_host(monkeypatch):
    ts = Scenario()
    ts.set_ruleset(
        "bulkwalk_hosts",
        [
            ([], ["bulkwalk_h"], {}),
        ],
    )
    ts.set_ruleset(
        "snmpv2c_hosts",
        [
            ([], ["v2c_h"], {}),
        ],
    )
    ts.add_host("bulkwalk_h")
    ts.add_host("v2c_h")
    ts.add_host("not_included")
    monkeypatch.setattr(config.HostConfig, "_is_inline_backend_supported", lambda _: True)

    config_cache = ts.apply(monkeypatch)

    # not bulkwalk and not v2c
    assert (
        config_cache.get_host_config("not_included").snmp_config("").snmp_backend
        == SNMPBackendEnum.CLASSIC
    )

    assert (
        config_cache.get_host_config("bulkwalk_h").snmp_config("").snmp_backend
        == SNMPBackendEnum.INLINE
    )

    assert (
        config_cache.get_host_config("v2c_h").snmp_config("").snmp_backend == SNMPBackendEnum.INLINE
    )

    # credentials is v3 -> INLINE
    monkeypatch.setattr(
        config.HostConfig,
        "_snmp_credentials",
        lambda _: (
            "a",
            "p",
        ),
    )
    assert (
        config_cache.get_host_config("not_included").snmp_config("").snmp_backend
        == SNMPBackendEnum.INLINE
    )
