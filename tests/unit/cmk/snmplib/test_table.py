#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
import logging
import socket
from collections.abc import Sequence
from functools import partial
from typing import NoReturn

import pytest
from pytest import MonkeyPatch

from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc.exceptions import MKSNMPError
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.log import logger
from cmk.utils.sectionname import SectionName

import cmk.snmplib._table as _snmp_table
from cmk.snmplib import (
    BackendOIDSpec,
    BackendSNMPTree,
    ensure_str,
    get_snmp_table,
    SNMPBackend,
    SNMPBackendEnum,
    SNMPContextConfig,
    SNMPContextTimeout,
    SNMPHostConfig,
    SNMPTable,
    SNMPVersion,
    SpecialColumn,
)

from cmk.checkengine.fetcher import SourceType

from cmk.base.config import ConfigCache

SNMPConfig = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname=HostName("testhost"),
    ipaddress=HostAddress("1.2.3.4"),
    credentials="",
    port=42,
    bulkwalk_enabled=True,
    snmp_version=SNMPVersion.V1,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits={},
    snmpv3_contexts=[],
    character_encoding="ascii",
    snmp_backend=SNMPBackendEnum.CLASSIC,
)


class SNMPTestBackend(SNMPBackend):
    def get(self, /, oid, *, context):
        pass

    def walk(self, /, oid, *, context, **kw):
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
            return get_snmp_table(
                section_name=SectionName("unit_test"),
                tree=info,
                walk_cache={},
                backend=backend,
                log=logger.debug,
            )
        return [
            get_snmp_table(
                section_name=SectionName("unit_test"),
                tree=i,
                walk_cache={},
                backend=backend,
                log=logger.debug,
            )
            for i in info
        ]

    assert get_all_snmp_tables(snmp_info) == expected_values


@pytest.mark.parametrize(
    "encoding, columns, expected",
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
    encoding: str | None,
    columns: _snmp_table._ResultColumnsSanitized,
    expected: Sequence[Sequence[_snmp_table.SNMPDecodedValues]],
) -> None:
    assert [
        _snmp_table._decode_column(c, v, partial(ensure_str, encoding=encoding)) for c, v in columns
    ] == expected


def test_use_advanced_snmp_version(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.set_ruleset(
        "bulkwalk_hosts",
        [{"condition": {"host_name": ["localhost"]}, "id": "01", "value": True}],
    )
    ts.add_host(HostName("abc"))
    ts.add_host(HostName("localhost"))
    config_cache = ts.apply(monkeypatch)
    assert (
        config_cache.make_snmp_config(
            HostName("abc"),
            socket.AddressFamily.AF_INET,
            HostAddress("1.2.3.4"),
            SourceType.HOST,
            backend_override=None,
        ).use_bulkwalk
        is False
    )
    assert (
        config_cache.make_snmp_config(
            HostName("localhost"),
            socket.AddressFamily.AF_INET,
            HostAddress("1.2.3.4"),
            SourceType.HOST,
            backend_override=None,
        ).use_bulkwalk
        is True
    )


def test_is_classic_at_snmp_v1_host(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.set_ruleset(
        "bulkwalk_hosts",
        [{"condition": {"host_name": ["bulkwalk_h"]}, "id": "01", "value": True}],
    )
    ts.set_ruleset(
        "snmpv2c_hosts",
        [{"condition": {"host_name": ["v2c_h"]}, "id": "02", "value": True}],
    )
    ts.add_host(HostName("bulkwalk_h"))
    ts.add_host(HostName("v2c_h"))
    ts.add_host(HostName("not_included"))
    ts.add_host(HostName("v3_h"))
    monkeypatch.setattr(ConfigCache, "_is_inline_backend_supported", lambda *args: True)

    config_cache = ts.apply(monkeypatch)

    # not bulkwalk and not v2c
    assert config_cache.get_snmp_backend(HostName("not_included")) is SNMPBackendEnum.INLINE
    assert config_cache.get_snmp_backend(HostName("bulkwalk_h")) is SNMPBackendEnum.INLINE
    assert config_cache.get_snmp_backend(HostName("v2c_h")) is SNMPBackendEnum.INLINE

    # credentials is v3 -> INLINE
    monkeypatch.setattr(ConfigCache, "_snmp_credentials", lambda *args: ("a", "p"))
    assert config_cache.get_snmp_backend(HostName("v3_h")) is SNMPBackendEnum.INLINE


def test_walk_passes_on_timeout_with_snmpv3_context_continue_on_timeout() -> None:
    class Backend(SNMPBackend):
        def get(self, /, *args: object, **kw: object) -> NoReturn:
            assert False

        def walk(self, /, *args: object, **kw: object) -> NoReturn:
            raise SNMPContextTimeout

    section_name = SectionName("section")
    with pytest.raises(MKSNMPError) as excinfo:
        _snmp_table.get_snmpwalk(
            section_name,
            ".1.2.3",
            ".4.5.6",
            walk_cache={},
            save_walk_cache=False,
            backend=Backend(
                dataclasses.replace(
                    SNMPConfig,
                    snmp_version=SNMPVersion.V3,
                    snmpv3_contexts=[
                        SNMPContextConfig(
                            section=section_name,
                            contexts=[""],
                            timeout_policy="continue",
                        )
                    ],
                ),
                logging.getLogger("test"),
            ),
            log=logger.debug,
        )

    assert type(excinfo.value) is not SNMPContextTimeout


def test_walk_raises_on_timeout_without_snmpv3_context_stop_on_timeout() -> None:
    class Backend(SNMPBackend):
        def get(self, /, *args: object, **kw: object) -> NoReturn:
            assert False

        def walk(self, /, *args: object, **kw: object) -> NoReturn:
            raise SNMPContextTimeout

    section_name = SectionName("section")
    with pytest.raises(MKSNMPError) as excinfo:
        _snmp_table.get_snmpwalk(
            section_name,
            ".1.2.3",
            ".4.5.6",
            walk_cache={},
            save_walk_cache=False,
            backend=Backend(
                dataclasses.replace(
                    SNMPConfig,
                    snmpv3_contexts=[
                        SNMPContextConfig(
                            section=section_name,
                            contexts=[""],
                            timeout_policy="stop",
                        )
                    ],
                ),
                logging.getLogger("test"),
            ),
            log=logger.debug,
        )

    assert type(excinfo.value) is SNMPContextTimeout
