#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
"netsnmp" python module (used for inline SNMP) and snmp commands (used for
classic SNMP) are not available in the git environment. For the moment it
does not make sense to build these tests as unit tests because we want to
tests the whole chain from single SNMP actions in our modules to the faked
SNMP device and back.
"""

import ast
import dataclasses
from collections.abc import Sequence
from pathlib import Path
from subprocess import CalledProcessError

import pytest

from tests.testlib.site import Site

from cmk.ccc.hostaddress import HostAddress

from cmk.snmplib import OID, SNMPBackendEnum, SNMPHostConfig, SNMPRowInfoForStoredWalk, SNMPVersion

from .snmp_helpers import default_config, get_single_oid


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid_ipv6(site: Site, backend_type: SNMPBackendEnum) -> None:
    if backend_type is SNMPBackendEnum.STORED_WALK:
        pytest.skip("Not relevant")

    config = dataclasses.replace(
        default_config(backend_type),
        is_ipv6_primary=True,
        ipaddress=HostAddress("::1"),
    )

    result, _ = get_single_oid(site, ".1.3.6.1.2.1.1.1.0", backend_type, config)
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid_snmpv3(site: Site, backend_type: SNMPBackendEnum) -> None:
    if backend_type is SNMPBackendEnum.STORED_WALK:
        pytest.skip("Not relevant")

    config = dataclasses.replace(
        default_config(backend_type),
        credentials=(
            "authNoPriv",
            "md5",
            "authOnlyUser",
            "authOnlyUser",
        ),
        snmp_version=SNMPVersion.V3,
    )

    result, _ = get_single_oid(site, ".1.3.6.1.2.1.1.1.0", backend_type, config)
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"


@pytest.mark.usefixtures("snmpsim")
@pytest.mark.parametrize("priv_proto, port", [("DES", 1341), ("AES-256", 1342), ("AES-192", 1343)])
def test_get_single_oid_snmpv3_higher_encryption(
    site: Site, backend_type: SNMPBackendEnum, priv_proto: str, port: int
) -> None:
    if backend_type is SNMPBackendEnum.STORED_WALK:
        pytest.skip("Not relevant")

    config = dataclasses.replace(
        default_config(backend_type),
        credentials=(
            "authPriv",
            "SHA-512",
            "authPrivUser",
            "A_long_authKey",
            priv_proto,
            "A_long_privKey",
        ),
        snmp_version=SNMPVersion.V3,
        # TODO: Reorganize snmp tests: at the moment we create *all* snmpsimd processes at setup
        #  but with different ports. Those different processes are then used in test_snmp_modes.py and
        #  backend_snmp.py...
        port=port,
    )

    result, _ = get_single_oid(site, ".1.3.6.1.2.1.1.1.0", backend_type, config)
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid_wrong_credentials(site: Site, backend_type: SNMPBackendEnum) -> None:
    if backend_type is SNMPBackendEnum.STORED_WALK:
        pytest.skip("Not relevant")

    config = dataclasses.replace(default_config(backend_type), credentials="dingdong")

    result, _ = get_single_oid(site, ".1.3.6.1.2.1.1.1.0", backend_type, config)
    assert result is None


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid(site: Site, backend_type: SNMPBackendEnum) -> None:
    result, _ = get_single_oid(
        site, ".1.3.6.1.2.1.1.1.0", backend_type, default_config(backend_type)
    )
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"
    assert isinstance(result, str)


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid_cache(site: Site, backend_type: SNMPBackendEnum) -> None:
    oid = ".1.3.6.1.2.1.1.1.0"
    expected_value = "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"

    value, cache = get_single_oid(site, oid, backend_type, default_config(backend_type))
    assert value == expected_value
    assert oid in cache
    cached_oid = cache[oid]
    assert cached_oid == expected_value
    assert isinstance(cached_oid, str)


@pytest.mark.usefixtures("snmpsim")
def test_get_single_non_prefixed_oid(site: Site, backend_type: SNMPBackendEnum) -> None:
    with pytest.raises(CalledProcessError) as e:
        get_single_oid(site, "1.3.6.1.2.1.1.1.0", backend_type, default_config(backend_type))
    assert "does not begin with" in e.value.stderr


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid_next(site: Site, backend_type: SNMPBackendEnum) -> None:
    assert (
        get_single_oid(site, ".1.3.6.1.2.1.1.9.1.*", backend_type, default_config(backend_type))[0]
        == ".1.3.6.1.6.3.10.3.1.1"
    )


# The get_single_oid function currently does not support OID_BIN handling
# @pytest.mark.usefixtures("snmpsim")
# def test_get_single_oid_hex(snmp_config) -> None:
#    assert get_single_oid(snmp_config, ".1.3.6.1.2.1.2.2.1.6.2")[0] == b"\x00\x12yb\xf9@"


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid_value(site: Site, backend_type: SNMPBackendEnum) -> None:
    assert (
        get_single_oid(site, ".1.3.6.1.2.1.1.9.1.2.1", backend_type, default_config(backend_type))[
            0
        ]
        == ".1.3.6.1.6.3.10.3.1.1"
    )


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid_not_existing(site: Site, backend_type: SNMPBackendEnum) -> None:
    assert (
        get_single_oid(site, ".1.3.100.200.300.400", backend_type, default_config(backend_type))[0]
        is None
    )


@pytest.mark.usefixtures("snmpsim")
def test_get_single_oid_not_resolvable(site: Site, backend_type: SNMPBackendEnum) -> None:
    if backend_type is SNMPBackendEnum.STORED_WALK:
        pytest.skip("Not relevant")

    config = dataclasses.replace(
        default_config(backend_type), ipaddress=HostAddress("unknown_host.internal.")
    )

    assert get_single_oid(site, ".1.3.6.1.2.1.1.7.0", backend_type, config)[0] is None


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
@pytest.mark.usefixtures("snmpsim")
def test_walk_for_export(
    site: Site, backend_type: SNMPBackendEnum, oid: OID, expected_table: Sequence[tuple[OID, str]]
) -> None:
    if backend_type is SNMPBackendEnum.STORED_WALK:
        pytest.skip("Not relevant")

    table = walk_for_export(site, oid, backend_type, default_config(backend_type))
    assert table == expected_table


def walk_for_export(
    site: Site, oid: OID, backend_type: SNMPBackendEnum, config: SNMPHostConfig
) -> SNMPRowInfoForStoredWalk:
    return ast.literal_eval(
        site.python_helper("helper_walk_for_export.py").check_output(
            input_=repr(
                (
                    oid,
                    backend_type.serialize(),
                    config.serialize(),
                    str(Path(__file__).parent.resolve() / "snmp_data" / "cmk-walk"),
                )
            )
        )
    )
