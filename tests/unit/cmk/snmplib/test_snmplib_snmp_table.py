#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest
from pytest import MonkeyPatch

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
    SNMPTable,
    SpecialColumn,
)

from cmk.checkers import SourceType

from cmk.base.config import ConfigCache

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
    snmp_backend=SNMPBackendEnum.CLASSIC,
)


class SNMPTestBackend(SNMPBackend):
    def get(self, oid, context_name=None):
        pass

    def walk(self, oid, section_name=None, table_base_oid=None, context_name=None):
        return [(f"{oid}.{r}", b"C0FEFE") for r in (1, 2, 3)]


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
def test_get_snmp_table(
    snmp_info: BackendSNMPTree, expected_values: list[Sequence[SNMPTable]]
) -> None:
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
def test_sanitize_snmp_encoding(
    monkeypatch: MonkeyPatch,
    encoding: str | None,
    columns: snmp_table.ResultColumnsSanitized,
    expected: snmp_table.ResultColumnsDecoded,
) -> None:
    ts = Scenario()
    ts.add_host(HostName("localhost"))
    ts.set_ruleset(
        "snmp_character_encodings",
        [
            {
                "condition": {},
                "value": encoding,
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)

    snmp_config = config_cache.make_snmp_config(HostName("localhost"), "", SourceType.HOST)
    assert snmp_table._sanitize_snmp_encoding(columns, snmp_config.ensure_str) == expected


def test_is_bulkwalk_host(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.set_ruleset(
        "bulkwalk_hosts",
        [{"condition": {"host_name": ["localhost"]}, "value": True}],
    )
    ts.add_host(HostName("abc"))
    ts.add_host(HostName("localhost"))
    config_cache = ts.apply(monkeypatch)
    assert (
        config_cache.make_snmp_config(HostName("abc"), "", SourceType.HOST).is_bulkwalk_host
        is False
    )
    assert (
        config_cache.make_snmp_config(HostName("localhost"), "", SourceType.HOST).is_bulkwalk_host
        is True
    )


def test_is_classic_at_snmp_v1_host(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.set_ruleset(
        "bulkwalk_hosts",
        [{"condition": {"host_name": ["bulkwalk_h"]}, "value": True}],
    )
    ts.set_ruleset(
        "snmpv2c_hosts",
        [{"condition": {"host_name": ["v2c_h"]}, "value": True}],
    )
    ts.add_host(HostName("bulkwalk_h"))
    ts.add_host(HostName("v2c_h"))
    ts.add_host(HostName("not_included"))
    monkeypatch.setattr(ConfigCache, "_is_inline_backend_supported", lambda *args: True)

    config_cache = ts.apply(monkeypatch)

    # not bulkwalk and not v2c
    assert config_cache.get_snmp_backend(HostName("not_included")) is SNMPBackendEnum.CLASSIC
    assert config_cache.get_snmp_backend(HostName("bulkwalk_h")) is SNMPBackendEnum.INLINE
    assert config_cache.get_snmp_backend(HostName("v2c_h")) is SNMPBackendEnum.INLINE

    # credentials is v3 -> INLINE
    monkeypatch.setattr(ConfigCache, "_snmp_credentials", lambda *args: ("a", "p"))
    assert config_cache.get_snmp_backend("not_included") is SNMPBackendEnum.INLINE
