#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections

import pytest  # type: ignore[import]

from cmk.utils.log import logger
from cmk.utils.exceptions import MKGeneralException

from cmk.snmplib.type_defs import SNMPHostConfig

from cmk.fetchers.snmp_backend import ClassicSNMPBackend
import cmk.fetchers.snmp_backend.classic as classic_snmp


@pytest.mark.parametrize("port,expected", [
    (161, ""),
    (1234, ":1234"),
])
def test_snmp_port_spec(port, expected):
    snmp_config = SNMPHostConfig(
        is_ipv6_primary=False,
        hostname="localhost",
        ipaddress="127.0.0.1",
        credentials="public",
        port=port,
        is_bulkwalk_host=False,
        is_snmpv2or3_without_bulkwalk_host=False,
        bulk_walk_size_of=10,
        timing={},
        oid_range_limits=[],
        snmpv3_contexts=[],
        character_encoding=None,
        is_usewalk_host=False,
        is_inline_snmp_host=False,
        record_stats=False,
    )
    assert ClassicSNMPBackend(snmp_config, logger)._snmp_port_spec() == expected


@pytest.mark.parametrize("is_ipv6,expected", [
    (True, "udp6:"),
    (False, ""),
])
def test_snmp_proto_spec(monkeypatch, is_ipv6, expected):
    snmp_config = SNMPHostConfig(
        is_ipv6_primary=is_ipv6,
        hostname="localhost",
        ipaddress="127.0.0.1",
        credentials="public",
        port=161,
        is_bulkwalk_host=False,
        is_snmpv2or3_without_bulkwalk_host=False,
        bulk_walk_size_of=10,
        timing={},
        oid_range_limits=[],
        snmpv3_contexts=[],
        character_encoding=None,
        is_usewalk_host=False,
        is_inline_snmp_host=False,
        record_stats=False,
    )
    assert ClassicSNMPBackend(snmp_config, logger)._snmp_proto_spec() == expected


SNMPSettings = collections.namedtuple("SNMPSettings", [
    "snmp_config",
    "context_name",
])


@pytest.mark.parametrize("settings,expected", [
    (SNMPSettings(
        snmp_config=SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="localhost",
            ipaddress="127.0.0.1",
            credentials="public",
            port=161,
            is_bulkwalk_host=True,
            is_snmpv2or3_without_bulkwalk_host=True,
            bulk_walk_size_of=10,
            timing={
                "timeout": 2,
                "retries": 3
            },
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            is_inline_snmp_host=False,
            record_stats=False,
        ),
        context_name=None,
    ), [
        'snmpbulkwalk', '-Cr10', '-v2c', '-c', 'public', '-m', '', '-M', '', '-t', '2.00', '-r',
        '3', '-Cc'
    ]),
    (SNMPSettings(
        snmp_config=SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="lohost",
            ipaddress="127.0.0.1",
            credentials="public",
            port=161,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=5,
            timing={
                "timeout": 5,
                "retries": 1
            },
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            is_inline_snmp_host=False,
            record_stats=False,
        ),
        context_name="blabla",
    ), [
        'snmpwalk', '-v1', '-c', 'public', '-m', '', '-M', '', '-t', '5.00', '-r', '1', '-n',
        'blabla', '-Cc'
    ]),
    (SNMPSettings(
        snmp_config=SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="lohost",
            ipaddress="public",
            credentials=("authNoPriv", "md5", "md5", "abc"),
            port=161,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=5,
            timing={
                "timeout": 5,
                "retries": 1
            },
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            is_inline_snmp_host=False,
            record_stats=False,
        ),
        context_name="blabla",
    ), [
        'snmpwalk', '-v3', '-l', 'authNoPriv', '-a', 'md5', '-u', 'md5', '-A', 'abc', '-m', '',
        '-M', '', '-t', '5.00', '-r', '1', '-n', 'blabla', '-Cc'
    ]),
    (SNMPSettings(
        snmp_config=SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="lohost",
            ipaddress="public",
            credentials=('noAuthNoPriv', 'secname'),
            port=161,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=5,
            timing={
                "timeout": 5,
                "retries": 1
            },
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            is_inline_snmp_host=False,
            record_stats=False,
        ),
        context_name=None,
    ), [
        'snmpwalk', '-v3', '-l', 'noAuthNoPriv', '-u', 'secname', '-m', '', '-M', '', '-t', '5.00',
        '-r', '1', '-Cc'
    ]),
    (SNMPSettings(
        snmp_config=SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="lohost",
            ipaddress="127.0.0.1",
            credentials=('authPriv', 'md5', 'secname', 'auhtpassword', 'DES', 'privacybla'),
            port=161,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=5,
            timing={
                "timeout": 5,
                "retries": 1
            },
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            is_inline_snmp_host=False,
            record_stats=False,
        ),
        context_name=None,
    ), [
        'snmpwalk', '-v3', '-l', 'authPriv', '-a', 'md5', '-u', 'secname', '-A', 'auhtpassword',
        '-x', 'DES', '-X', 'privacybla', '-m', '', '-M', '', '-t', '5.00', '-r', '1', '-Cc'
    ]),
])
def test_snmp_walk_command(monkeypatch, settings, expected):
    backend = ClassicSNMPBackend(settings.snmp_config, logger)
    assert backend._snmp_walk_command(settings.context_name) == expected


@pytest.mark.parametrize("proto, result", [
    ("md5", "md5"),
    ("sha", "sha"),
    ("SHA-224", "SHA-224"),
    ("SHA-256", "SHA-256"),
    ("SHA-384", "SHA-384"),
    ("SHA-512", "SHA-512"),
])
def test_auth_proto(proto, result):
    assert classic_snmp._auth_proto_for(proto) == result


def test_auth_proto_unknown():
    with pytest.raises(MKGeneralException):
        classic_snmp._auth_proto_for("unknown")


@pytest.mark.parametrize("proto, result", [
    ("DES", "DES"),
    ("AES", "AES"),
])
def test_priv_proto(proto, result):
    assert classic_snmp._priv_proto_for(proto) == result


@pytest.mark.parametrize("proto", [
    "",
    "unknown",
    "3DES-EDE",
    "AES-192",
    "AES-256",
    "AES-192-Blumenthal",
    "AES-256-Blumenthal",
])
def test_priv_proto_unknown(proto):
    with pytest.raises(MKGeneralException):
        classic_snmp._priv_proto_for(proto)
