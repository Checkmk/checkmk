#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import NoReturn

import cmk.fetchers._snmp._scan as snmp_scan
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.snmplib import (
    SNMPBackend,
    SNMPBackendEnum,
    SNMPHostConfig,
    SNMPSectionName,
    SNMPVersion,
)

SNMP_CONFIG = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname=HostName("testhost"),
    ipaddress=HostAddress("1.2.3.4"),
    credentials="",
    port=42,
    bulkwalk_enabled=True,
    snmp_version=SNMPVersion.V2C,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits={},
    snmpv3_contexts=[],
    character_encoding="ascii",
    snmp_backend=SNMPBackendEnum.CLASSIC,
)


# Adapted from `test_snmplib_snmp_table`.
class SNMPTestBackend(SNMPBackend):
    def __init__(self) -> None:
        super().__init__(SNMP_CONFIG, logging.getLogger())

    def get(self, /, *_a: object, **_kw: object) -> None:
        # See also: `snmp_mode.get_single_oid()`
        return None

    def walk(self, /, *_a: object, **_kw: object) -> NoReturn:
        raise NotImplementedError("walk")


# Cache OIDs to avoid actual SNMP I/O.
FAKE_OID_CACHE = {
    snmp_scan.OID_SYS_DESCR: "sys description",
    snmp_scan.OID_SYS_OBJ: "sys object",
}

# Sections with explicit detect specs for testing scan logic.
# The first three match any sys-description value (including empty string),
# the last one requires an OID that is never present in the test backend.
_SNMP_SECTIONS: list[snmp_scan.SNMPScanSection] = [
    (SNMPSectionName("hr_mem"), [[(snmp_scan.OID_SYS_DESCR, ".*", True)]]),
    (SNMPSectionName("snmp_info"), [[(snmp_scan.OID_SYS_DESCR, ".*", True)]]),
    (SNMPSectionName("snmp_uptime"), [[(snmp_scan.OID_SYS_DESCR, ".*", True)]]),
    (SNMPSectionName("not_detected"), [[(".1.3.6.1.99.99.99", "some_value", True)]]),
]


def test_snmp_scan_find_plugins__success() -> None:
    found = snmp_scan._find_sections(  # noqa: SLF001  # FIXME by not testing private members...
        _SNMP_SECTIONS,
        FAKE_OID_CACHE,
        on_error=OnError.RAISE,
        backend=SNMPTestBackend(),
    )

    assert _SNMP_SECTIONS
    assert found
    assert len(_SNMP_SECTIONS) > len(found)


def test_gather_available_raw_section_names_defaults() -> None:
    assert snmp_scan.gather_available_raw_section_names(
        _SNMP_SECTIONS,
        scan_config=snmp_scan.SNMPScanConfig(
            on_error=OnError.RAISE,
            missing_sys_description=True,
        ),
        backend=SNMPTestBackend(),
    ) == {
        SNMPSectionName("hr_mem"),
        SNMPSectionName("snmp_info"),
        SNMPSectionName("snmp_uptime"),
    }
