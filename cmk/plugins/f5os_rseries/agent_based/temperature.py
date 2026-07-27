#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# F5OS rSeries platform temperature
# MIB: F5-PLATFORM-STATS-MIB (enterprise .1.3.6.1.4.1.12276.1)

from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.f5os_rseries.lib.detect import DETECT_F5OS_RSERIES
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def _decode_oid_octetstring(oid_suffix: str) -> str:
    """Decode a length-prefixed OctetString OID sub-identifier to a printable string.

    F5OS tables index rows with OctetString sub-identifiers, e.g. "platform" is
    encoded as "8.112.108.97.116.102.111.114.109" (length byte followed by ASCII codes).
    """
    parts = oid_suffix.split(".")
    try:
        length = int(parts[0])
        chars = [int(b) for b in parts[1 : 1 + length]]
        decoded = "".join(chr(c) for c in chars if 32 <= c < 127)
        return decoded if decoded else oid_suffix
    except (ValueError, IndexError):
        return oid_suffix


@dataclass(frozen=True)
class F5OSTempReading:
    current: float  # tempCurrent (°C)
    average: float  # tempAverage (°C)
    minimum: float  # tempMinimum (°C)
    maximum: float  # tempMaximum (°C)


def parse_f5os_rseries_temp(string_table: StringTable) -> dict[str, F5OSTempReading]:
    result: dict[str, F5OSTempReading] = {}
    for row in string_table:
        # OIDEnd is an OctetString-encoded name, e.g. "8.112.108.97.116.102.111.114.109" → "platform"
        item = _decode_oid_octetstring(row[0])
        result[item] = F5OSTempReading(
            current=float(row[1]) / 10.0,  # tempCurrent (unit: 0.1°C)
            average=float(row[2]) / 10.0,  # tempAverage (unit: 0.1°C)
            minimum=float(row[3]) / 10.0,  # tempMinimum (unit: 0.1°C)
            maximum=float(row[4]) / 10.0,  # tempMaximum (unit: 0.1°C)
        )
    return result


snmp_section_f5os_rseries_temp = SimpleSNMPSection(
    name="f5os_rseries_temp",
    parse_function=parse_f5os_rseries_temp,
    detect=DETECT_F5OS_RSERIES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12276.1.2.1.3.1.1",
        oids=[
            OIDEnd(),  # OctetString-encoded row index (e.g. "platform")
            "2",  # tempCurrent (unit: 0.1°C)
            "3",  # tempAverage (unit: 0.1°C)
            "4",  # tempMinimum (unit: 0.1°C)
            "5",  # tempMaximum (unit: 0.1°C)
        ],
    ),
)


def discover_f5os_rseries_temp(section: dict[str, F5OSTempReading]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_f5os_rseries_temp(
    item: str, params: TempParamType, section: dict[str, F5OSTempReading]
) -> CheckResult:
    data = section.get(item)
    if data is None:
        return
    yield from check_temperature(data.current, params)
    yield Result(
        state=State.OK,
        notice=(
            f"Average: {data.average:.1f} °C; "
            f"Min: {data.minimum:.1f} °C; "
            f"Max: {data.maximum:.1f} °C"
        ),
    )
    yield Metric("temp_avg", data.average)
    yield Metric("temp_max", data.maximum)


check_plugin_f5os_rseries_temp = CheckPlugin(
    name="f5os_rseries_temp",
    sections=["f5os_rseries_temp"],
    service_name="F5OS Platform Temperature %s",
    discovery_function=discover_f5os_rseries_temp,
    check_function=check_f5os_rseries_temp,
    check_default_parameters={"levels": (35.0, 45.0)},
    check_ruleset_name="temperature",
)
