#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from typing import NamedTuple

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.log import logger

from cmk.snmplib import SNMPBackendEnum, SNMPHostConfig, SNMPVersion

import cmk.fetchers.snmp_backend.classic as classic_snmp
from cmk.fetchers.snmp_backend import ClassicSNMPBackend


@pytest.mark.parametrize(
    "port,expected",
    [
        (161, ""),
        (1234, ":1234"),
    ],
)
def test_snmp_port_spec(port: int, expected: str) -> None:
    snmp_config = SNMPHostConfig(
        is_ipv6_primary=False,
        hostname=HostName("localhost"),
        ipaddress=HostAddress("127.0.0.1"),
        credentials="public",
        port=port,
        bulkwalk_enabled=True,
        snmp_version=SNMPVersion.V2C,
        bulk_walk_size_of=10,
        timing={},
        oid_range_limits={},
        snmpv3_contexts=[],
        character_encoding=None,
        snmp_backend=SNMPBackendEnum.CLASSIC,
    )
    assert ClassicSNMPBackend(snmp_config, logger)._snmp_port_spec() == expected


@pytest.mark.usefixtures("monkeypatch")
@pytest.mark.parametrize(
    "is_ipv6,expected",
    [
        (True, "udp6:"),
        (False, ""),
    ],
)
def test_snmp_proto_spec(is_ipv6: bool, expected: str) -> None:
    snmp_config = SNMPHostConfig(
        is_ipv6_primary=is_ipv6,
        hostname=HostName("localhost"),
        ipaddress=HostAddress("127.0.0.1"),
        credentials="public",
        port=161,
        bulkwalk_enabled=True,
        snmp_version=SNMPVersion.V2C,
        bulk_walk_size_of=10,
        timing={},
        oid_range_limits={},
        snmpv3_contexts=[],
        character_encoding=None,
        snmp_backend=SNMPBackendEnum.CLASSIC,
    )
    assert ClassicSNMPBackend(snmp_config, logger)._snmp_proto_spec() == expected


class SNMPSettings(NamedTuple):
    snmp_config: SNMPHostConfig
    context_name: str


@pytest.mark.usefixtures("monkeypatch")
@pytest.mark.parametrize(
    "settings,expected",
    [
        (
            SNMPSettings(
                snmp_config=SNMPHostConfig(
                    is_ipv6_primary=False,
                    hostname=HostName("localhost"),
                    ipaddress=HostAddress("127.0.0.1"),
                    credentials="public",
                    port=161,
                    bulkwalk_enabled=False,
                    snmp_version=SNMPVersion.V2C,
                    bulk_walk_size_of=10,
                    timing={"timeout": 2, "retries": 3},
                    oid_range_limits={},
                    snmpv3_contexts=[],
                    character_encoding=None,
                    snmp_backend=SNMPBackendEnum.CLASSIC,
                ),
                context_name="",
            ),
            [
                "snmpwalk",
                "-v2c",
                "-c",
                "public",
                "-m",
                "",
                "-M",
                "",
                "-t",
                "2.00",
                "-r",
                "3",
            ],
        ),
        (
            SNMPSettings(
                snmp_config=SNMPHostConfig(
                    is_ipv6_primary=False,
                    hostname=HostName("lohost"),
                    ipaddress=HostAddress("127.0.0.1"),
                    credentials="public",
                    port=161,
                    bulkwalk_enabled=True,
                    snmp_version=SNMPVersion.V1,
                    bulk_walk_size_of=5,
                    timing={"timeout": 5, "retries": 1},
                    oid_range_limits={},
                    snmpv3_contexts=[],
                    character_encoding=None,
                    snmp_backend=SNMPBackendEnum.CLASSIC,
                ),
                context_name="blabla",
            ),
            [
                "snmpwalk",
                "-v1",
                "-c",
                "public",
                "-m",
                "",
                "-M",
                "",
                "-t",
                "5.00",
                "-r",
                "1",
                "-n",
                "blabla",
            ],
        ),
        (
            SNMPSettings(
                snmp_config=SNMPHostConfig(
                    is_ipv6_primary=False,
                    hostname=HostName("lohost"),
                    ipaddress=HostAddress("1.2.3.4"),
                    credentials=("authNoPriv", "md5", "md5", "abc"),
                    port=161,
                    bulkwalk_enabled=True,
                    snmp_version=SNMPVersion.V3,
                    bulk_walk_size_of=5,
                    timing={"timeout": 5, "retries": 1},
                    oid_range_limits={},
                    snmpv3_contexts=[],
                    character_encoding=None,
                    snmp_backend=SNMPBackendEnum.CLASSIC,
                ),
                context_name="blabla",
            ),
            [
                "snmpbulkwalk",
                "-Cr5",
                "-v3",
                "-l",
                "authNoPriv",
                "-a",
                "md5",
                "-u",
                "md5",
                "-A",
                "abc",
                "-m",
                "",
                "-M",
                "",
                "-t",
                "5.00",
                "-r",
                "1",
                "-n",
                "blabla",
            ],
        ),
        (
            SNMPSettings(
                snmp_config=SNMPHostConfig(
                    is_ipv6_primary=False,
                    hostname=HostName("lohost"),
                    ipaddress=HostAddress("1.2.3.4"),
                    credentials=("noAuthNoPriv", "secname"),
                    port=161,
                    bulkwalk_enabled=True,
                    snmp_version=SNMPVersion.V3,
                    bulk_walk_size_of=5,
                    timing={"timeout": 5, "retries": 1},
                    oid_range_limits={},
                    snmpv3_contexts=[],
                    character_encoding=None,
                    snmp_backend=SNMPBackendEnum.CLASSIC,
                ),
                context_name="",
            ),
            [
                "snmpbulkwalk",
                "-Cr5",
                "-v3",
                "-l",
                "noAuthNoPriv",
                "-u",
                "secname",
                "-m",
                "",
                "-M",
                "",
                "-t",
                "5.00",
                "-r",
                "1",
            ],
        ),
        (
            SNMPSettings(
                snmp_config=SNMPHostConfig(
                    is_ipv6_primary=False,
                    hostname=HostName("lohost"),
                    ipaddress=HostAddress("127.0.0.1"),
                    credentials=("authPriv", "md5", "secname", "auhtpassword", "DES", "privacybla"),
                    port=161,
                    bulkwalk_enabled=True,
                    snmp_version=SNMPVersion.V3,
                    bulk_walk_size_of=5,
                    timing={"timeout": 5, "retries": 1},
                    oid_range_limits={},
                    snmpv3_contexts=[],
                    character_encoding=None,
                    snmp_backend=SNMPBackendEnum.CLASSIC,
                ),
                context_name="",
            ),
            [
                "snmpbulkwalk",
                "-Cr5",
                "-v3",
                "-l",
                "authPriv",
                "-a",
                "md5",
                "-u",
                "secname",
                "-A",
                "auhtpassword",
                "-x",
                "DES",
                "-X",
                "privacybla",
                "-m",
                "",
                "-M",
                "",
                "-t",
                "5.00",
                "-r",
                "1",
            ],
        ),
    ],
)
def test_snmp_walk_command(settings: SNMPSettings, expected: Sequence[str]) -> None:
    backend = ClassicSNMPBackend(settings.snmp_config, logger)
    assert backend._snmp_base_command("snmpwalk", settings.context_name) == expected


@pytest.mark.parametrize(
    "proto, result",
    [
        ("md5", "md5"),
        ("sha", "sha"),
        ("SHA-224", "SHA-224"),
        ("SHA-256", "SHA-256"),
        ("SHA-384", "SHA-384"),
        ("SHA-512", "SHA-512"),
    ],
)
def test_auth_proto(proto: str, result: str) -> None:
    assert classic_snmp._auth_proto_for(proto) == result


def test_auth_proto_unknown() -> None:
    with pytest.raises(MKGeneralException):
        classic_snmp._auth_proto_for("unknown")


@pytest.mark.parametrize(
    "proto, result",
    [
        ("DES", "DES"),
        ("AES", "AES"),
        ("AES-256", "AES-256"),
        ("AES-192", "AES-192"),
    ],
)
def test_priv_proto(proto: str, result: str) -> None:
    assert classic_snmp._priv_proto_for(proto) == result


@pytest.mark.parametrize(
    "proto",
    [
        "",
        "unknown",
        "3DES-EDE",
        "AES-192-Blumenthal",
        "AES-256-Blumenthal",
    ],
)
def test_priv_proto_unknown(proto: str) -> None:
    with pytest.raises(MKGeneralException):
        classic_snmp._priv_proto_for(proto)
