#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.exceptions import MKGeneralException

import cmk.snmplib.snmp_cache as snmp_cache
import cmk.snmplib.snmp_modes as snmp_modes

# "netsnmp" python module (used for inline SNMP) and snmp commands (used for
# classic SNMP) are not available in the git environment. For the moment it
# does not make sense to build these tests as unit tests because we want to
# tests the whole chain from single SNMP actions in our modules to the faked
# SNMP device and back.


# Found no other way to achieve this
# https://github.com/pytest-dev/pytest/issues/363
@pytest.fixture(scope="module")
def monkeymodule(request):
    # pylint: disable=import-outside-toplevel
    from _pytest.monkeypatch import MonkeyPatch  # type: ignore[import]

    # pylint: enable=import-outside-toplevel
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


def test_get_single_oid_ipv6(backend) -> None:
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(
        is_ipv6_primary=True,
        ipaddress="::1",
    )

    result = snmp_modes.get_single_oid(".1.3.6.1.2.1.1.1.0", backend=backend)
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"


def test_get_single_oid_snmpv3(backend) -> None:
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(
        credentials=(
            "authNoPriv",
            "md5",
            "authOnlyUser",
            "authOnlyUser",
        )
    )

    result = snmp_modes.get_single_oid(".1.3.6.1.2.1.1.1.0", backend=backend)
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"


def test_get_single_oid_snmpv3_higher_encryption(backend) -> None:
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(
        credentials=(
            "authPriv",
            "SHA-512",
            "authPrivUser",
            "A_long_authKey",
            "DES",
            "A_long_privKey",
        ),
    )

    # TODO: Reorganize snmp tests: at the moment we create *all* snmpsimd processes at setup
    #  but with different ports. Those different processes are then used in test_snmp_modes.py and
    #  backend_snmp.py...
    backend.port = 1341

    result = snmp_modes.get_single_oid(".1.3.6.1.2.1.1.1.0", backend=backend)
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"


def test_get_single_oid_wrong_credentials(backend) -> None:
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(credentials="dingdong")

    result = snmp_modes.get_single_oid(".1.3.6.1.2.1.1.1.0", backend=backend)
    assert result is None


def test_get_single_oid(backend) -> None:
    result = snmp_modes.get_single_oid(".1.3.6.1.2.1.1.1.0", backend=backend)
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"
    assert isinstance(result, str)


def test_get_single_oid_cache(backend) -> None:
    oid = ".1.3.6.1.2.1.1.1.0"
    expected_value = "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"

    assert snmp_modes.get_single_oid(oid, backend=backend) == expected_value
    assert oid in snmp_cache.single_oid_cache()
    cached_oid = snmp_cache.single_oid_cache()[oid]
    assert cached_oid == expected_value
    assert isinstance(cached_oid, str)


def test_get_single_non_prefixed_oid(backend) -> None:
    with pytest.raises(MKGeneralException, match="does not begin with"):
        snmp_modes.get_single_oid("1.3.6.1.2.1.1.1.0", backend=backend)


def test_get_single_oid_next(backend) -> None:
    assert (
        snmp_modes.get_single_oid(".1.3.6.1.2.1.1.9.1.*", backend=backend)
        == ".1.3.6.1.6.3.10.3.1.1"
    )


# The get_single_oid function currently does not support OID_BIN handling
# def test_get_single_oid_hex(snmp_config) -> None:
#    assert snmp_modes.get_single_oid(snmp_config, ".1.3.6.1.2.1.2.2.1.6.2") == b"\x00\x12yb\xf9@"


def test_get_single_oid_value(backend) -> None:
    assert (
        snmp_modes.get_single_oid(".1.3.6.1.2.1.1.9.1.2.1", backend=backend)
        == ".1.3.6.1.6.3.10.3.1.1"
    )


def test_get_single_oid_not_existing(backend) -> None:
    assert snmp_modes.get_single_oid(".1.3.100.200.300.400", backend=backend) is None


def test_get_single_oid_not_resolvable(backend) -> None:
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(ipaddress="bla.local")

    assert snmp_modes.get_single_oid(".1.3.6.1.2.1.1.7.0", backend=backend) is None


@pytest.mark.parametrize(
    "oid,expected_table",
    [
        (
            ".1.3.6.1.2.1.11",
            [
                (".1.3.6.1.2.1.11.1.0", "4294967295"),
                (".1.3.6.1.2.1.11.2.0", "4294967295"),
                (".1.3.6.1.2.1.11.3.0", "877474094"),
                (".1.3.6.1.2.1.11.4.0", "292513791"),
                (".1.3.6.1.2.1.11.5.0", "584997545"),
                (".1.3.6.1.2.1.11.6.0", "292504432"),
                (".1.3.6.1.2.1.11.8.0", "877498609"),
                (".1.3.6.1.2.1.11.9.0", "585006643"),
                (".1.3.6.1.2.1.11.10.0", "585006444"),
                (".1.3.6.1.2.1.11.11.0", "292505902"),
                (".1.3.6.1.2.1.11.12.0", "315362353"),
                (".1.3.6.1.2.1.11.13.0", "4294967295"),
            ],
        ),
        (
            ".1.3.6.1.2.1.1.9.1.3",
            [
                (".1.3.6.1.2.1.1.9.1.3.1", "The SNMP Management Architecture MIB."),
                (".1.3.6.1.2.1.1.9.1.3.2", "The MIB for Message Processing and Dispatching."),
                (
                    ".1.3.6.1.2.1.1.9.1.3.3",
                    "The management information definitions for the SNMP User-based Security Model.",
                ),
                (".1.3.6.1.2.1.1.9.1.3.4", "The MIB module for SNMPv2 entities"),
                (".1.3.6.1.2.1.1.9.1.3.5", "The MIB module for managing TCP implementations"),
                (
                    ".1.3.6.1.2.1.1.9.1.3.6",
                    "The MIB module for managing IP and ICMP implementations",
                ),
                (".1.3.6.1.2.1.1.9.1.3.7", "The MIB module for managing UDP implementations"),
                (".1.3.6.1.2.1.1.9.1.3.8", "View-based Access Control Model for SNMP."),
            ],
        ),
        (
            ".1.3.6.1.2.1.4.21.1.1",
            [
                (".1.3.6.1.2.1.4.21.1.1.0.0.0.0", "0.0.0.0"),
                (".1.3.6.1.2.1.4.21.1.1.127.0.0.0", "127.0.0.0"),
                (".1.3.6.1.2.1.4.21.1.1.195.218.254.0", "195.218.254.0"),
            ],
        ),
        (
            ".1.3.6.1.2.1.2.2.1.6",
            [
                (".1.3.6.1.2.1.2.2.1.6.1", ""),
                (".1.3.6.1.2.1.2.2.1.6.2", '"00 12 79 62 F9 40 "'),
            ],
        ),
    ],
)
def test_walk_for_export(backend, oid, expected_table) -> None:
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    table = snmp_modes.walk_for_export(oid, backend=backend)
    assert table == expected_table
