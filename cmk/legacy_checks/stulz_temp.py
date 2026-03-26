#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1170.1.1.1 220 --> Stulz-WIB8000-MIB::unitAirTemperature.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1170.1.2.1 216 --> Stulz-WIB8000-MIB::unitAirTemperature.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1175.1.1.1 220 --> Stulz-WIB8000-MIB::unitSetpointAirTratureCorrected.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1175.1.2.1 220 --> Stulz-WIB8000-MIB::unitSetpointAirTratureCorrected.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1192.1.1.1 221 --> Stulz-WIB8000-MIB::unitReturnAirTemperature.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1192.1.2.1 216 --> Stulz-WIB8000-MIB::unitReturnAirTemperature.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1193.1.1.1 220 --> Stulz-WIB8000-MIB::unitSupplyAirTemperature.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1193.1.2.1 214 --> Stulz-WIB8000-MIB::unitSupplyAirTemperature.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1.1.1196.1.2.1 83 --> Stulz-WIB8000-MIB::unitOutsideAirTemperature.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1171.1.1.1 418 --> Stulz-WIB8000-MIB::unitHumidity.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1171.1.2.1 420 --> Stulz-WIB8000-MIB::unitHumidity.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1178.1.1.1 500 --> Stulz-WIB8000-MIB::unitSetpointHumidityCorrected.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1178.1.2.1 500 --> Stulz-WIB8000-MIB::unitSetpointHumidityCorrected.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1194.1.1.1 418 --> Stulz-WIB8000-MIB::unitReturnAirHumidity.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1194.1.2.1 419 --> Stulz-WIB8000-MIB::unitReturnAirHumidity.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1195.1.1.1 421 --> Stulz-WIB8000-MIB::unitSupplyAirHumidity.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1195.1.2.1 425 --> Stulz-WIB8000-MIB::unitSupplyAirHumidity.1.2.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.3.1.1.1208.1.1.1 11 --> Stulz-WIB8000-MIB::currentRaisedFloorPressure.1.1.1
# .1.3.6.1.4.1.29462.10.2.1.1.1.1.3.1.1.1208.1.2.1 16 --> Stulz-WIB8000-MIB::currentRaisedFloorPressure.1.2.1


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.stulz.lib import DETECT_STULZ

Section = Mapping[str, float]

_MAP_TYPES = {
    "1170": "unit air",
    "1192": "unit return air",
    "1193": "unit supply air",
    "1196": "unit outside air",
    "1243": "unit supply 3",
    "1244": "unit return air 2",
    "1245": "unit return air 3",
    "1246": "unit return air temrn",
    "1247": "unit return air temly",
    "1248": "unit supply air 2",
    "10210": "condensor",
    "10211": "supply 1",
    "10212": "supply 2",
    "10264": "FCB room air",
    "10266": "supply air comfort unit 1",
    "10267": "supply air comfort unit 2",
    "10268": "FCB outside air",
}


def parse_stulz_temp(string_table: StringTable) -> Section:
    parsed: dict[str, float] = {}
    for oidend, reading_str in string_table:
        oids = oidend.split(".")
        temp_ty = oids[0]
        index = oids[2]
        if temp_ty in _MAP_TYPES and reading_str != "999":
            itemname = f"{_MAP_TYPES[temp_ty]}-{index}"
            parsed.setdefault(itemname, float(reading_str) / 10)
    return parsed


def discover_stulz_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_stulz_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if item in section:
        yield from check_temperature(
            section[item],
            params,
            unique_name=f"stulz_temp_{item}",
            value_store=get_value_store(),
        )


snmp_section_stulz_temp = SimpleSNMPSection(
    name="stulz_temp",
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1",
        oids=[OIDEnd(), "1"],
    ),
    parse_function=parse_stulz_temp,
)

check_plugin_stulz_temp = CheckPlugin(
    name="stulz_temp",
    service_name="Temperature %s",
    discovery_function=discover_stulz_temp,
    check_function=check_stulz_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (25.0, 28.0)},
)
