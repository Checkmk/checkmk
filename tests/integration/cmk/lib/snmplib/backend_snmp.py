#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import pytest  # type: ignore[import]
from cmk.snmplib.type_defs import ABCSNMPBackend, OID, SNMPHostConfig, SNMPRawValue
from typing import List, Tuple, Optional, Type

try:
    from cmk.fetchers.cee.snmp_backend.inline import InlineSNMPBackend
except ImportError:
    InlineSNMPBackend = None  # type: ignore[assignment, misc]

try:
    from cmk.fetchers.cee.snmp_backend.pysnmp_backend import PySNMPBackend
except ImportError:
    PySNMPBackend = None  # type: ignore[assignment, misc]

from cmk.fetchers.snmp_backend.classic import ClassicSNMPBackend

logger = logging.getLogger(__name__)

#.
#   .--Tests---------------------------------------------------------------.
#   |                         _____         _                              |
#   |                        |_   _|__  ___| |_ ___                        |
#   |                          | |/ _ \/ __| __/ __|                       |
#   |                          | |  __/\__ \ |_\__ \                       |
#   |                          |_|\___||___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Tests that compare Inline, PySNMP and Classic output                 |
#   '----------------------------------------------------------------------'


@pytest.mark.parametrize("oid", [
    (".1.3.6.1.2.1.4.12.0"),
    (".1.3.6.1.2.1.2.2.1.6.1"),
    (".1.3.6.1.2.1.2.2.1.6.*"),
])
def test_get_ipv4(oid: OID):
    configs = _create_configs_ipv4()
    result_pysnmp, result_inline, result_classic = _create_results_snmpbackend_get(oid, configs)

    assert result_pysnmp == result_inline == result_classic


@pytest.mark.parametrize("oid", [
    (".1.3.6.1.2.1.4.12.0"),
    (".1.3.6.1.2.1.2.2.1.6.1"),
])
def test_get_ipv6(oid: OID):
    configs = _create_configs_ipv6()
    result_pysnmp, result_inline, result_classic = _create_results_snmpbackend_get(oid, configs)

    assert result_pysnmp == result_inline == result_classic


@pytest.mark.parametrize("oid", [
    (".1.3.6.1.2.1.4.12.0"),
    (".1.3.6.1.2.1.2.2.1.6.1"),
])
def test_get_auth(oid: OID):
    configs = _create_configs_special_auth()
    result_pysnmp, result_inline, result_classic = _create_results_snmpbackend_get(oid, configs)

    assert result_pysnmp == result_inline == result_classic


#.
#   .--Helpers-------------------------------------------------------------.
#   |                    _   _      _                                      |
#   |                   | | | | ___| |_ __   ___ _ __ ___                  |
#   |                   | |_| |/ _ \ | '_ \ / _ \ '__/ __|                 |
#   |                   |  _  |  __/ | |_) |  __/ |  \__ \                 |
#   |                   |_| |_|\___|_| .__/ \___|_|  |___/                 |
#   |                                |_|                                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Helpers that create results                                          |
#   '----------------------------------------------------------------------'


def _create_results_snmpbackend_get(
    oid: str, configs: List[SNMPHostConfig]
) -> Tuple[List[Optional[SNMPRawValue]], List[Optional[SNMPRawValue]],
           List[Optional[SNMPRawValue]]]:

    return (
        [_create_result_for_backend(PySNMPBackend, oid, c) for c in configs],
        [_create_result_for_backend(InlineSNMPBackend, oid, c) for c in configs],
        [_create_result_for_backend(ClassicSNMPBackend, oid, c) for c in configs],
    )


def _create_result_for_backend(backend: Type[ABCSNMPBackend], oid: OID,
                               config: SNMPHostConfig) -> Optional[SNMPRawValue]:
    return backend(config, logger).get(oid,
                                       context_name="public" if config.is_ipv6_primary and
                                       not isinstance(config.credentials, str) else "")


#.
#   .--Configs-------------------------------------------------------------.
#   |                   ____             __ _                              |
#   |                  / ___|___  _ __  / _(_) __ _ ___                    |
#   |                 | |   / _ \| '_ \| |_| |/ _` / __|                   |
#   |                 | |__| (_) | | | |  _| | (_| \__ \                   |
#   |                  \____\___/|_| |_|_| |_|\__, |___/                   |
#   |                                         |___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Different configs for tests                                          |
#   '----------------------------------------------------------------------'


def _create_configs_ipv4() -> List[SNMPHostConfig]:
    return [
        SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="ipv4/snmpv1",
            ipaddress="127.0.0.1",
            credentials="public",
            port=1337,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=10,
            timing={},
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend="classic",
            record_stats=False,
        ),
        SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="ipv4/snmpv2",
            ipaddress="127.0.0.1",
            credentials="public",
            port=1337,
            is_bulkwalk_host=True,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=10,
            timing={},
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend="classic",
            record_stats=False,
        ),
        SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="ipv4/snmpv3",
            ipaddress="127.0.0.1",
            credentials=(
                "authPriv",
                "md5",
                "md5desuser",
                "md5password",
                "DES",
                "desencryption",
            ),
            port=1338,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=10,
            timing={},
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend="classic",
            record_stats=False,
        ),
    ]


def _create_configs_ipv6() -> List[SNMPHostConfig]:
    return [
        SNMPHostConfig(
            is_ipv6_primary=True,
            hostname="ipv6/snmpv1",
            ipaddress="::1",
            credentials="public",
            port=1337,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=10,
            timing={},
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend="classic",
            record_stats=False,
        ),
        SNMPHostConfig(
            is_ipv6_primary=True,
            hostname="ipv6/snmpv2",
            ipaddress="::1",
            credentials="public",
            port=1337,
            is_bulkwalk_host=True,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=10,
            timing={},
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend="classic",
            record_stats=False,
        ),
        SNMPHostConfig(
            is_ipv6_primary=True,
            hostname="ipv6/snmpv3",
            ipaddress="::1",
            credentials=(
                "authPriv",
                "sha",
                "shaaesuser",
                "shapassword",
                "AES",
                "aesencryption",
            ),
            port=1340,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=10,
            timing={},
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend="classic",
            record_stats=False,
        ),
    ]


def _create_configs_special_auth() -> List[SNMPHostConfig]:
    return [
        SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="noauthnopriv",
            ipaddress="127.0.0.1",
            credentials=(
                "noAuthNoPriv",
                "noAuthNoPrivUser",
            ),
            port=1339,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=10,
            timing={},
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend="classic",
            record_stats=False,
        ),
        SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="authonly",
            ipaddress="127.0.0.1",
            credentials=(
                "authNoPriv",
                "md5",
                "authOnlyUser",
                "authOnlyUser",
            ),
            port=1337,
            is_bulkwalk_host=False,
            is_snmpv2or3_without_bulkwalk_host=False,
            bulk_walk_size_of=10,
            timing={},
            oid_range_limits=[],
            snmpv3_contexts=[],
            character_encoding=None,
            is_usewalk_host=False,
            snmp_backend="classic",
            record_stats=False,
        ),
    ]
