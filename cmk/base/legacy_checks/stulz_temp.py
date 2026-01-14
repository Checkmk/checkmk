#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.stulz.lib import DETECT_STULZ

check_info = {}

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


def parse_stulz_temp(string_table):
    map_types = {
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

    parsed = {}
    for oidend, reading_str in string_table:
        oids = oidend.split(".")
        temp_ty = oids[0]
        index = oids[2]
        if temp_ty in map_types and reading_str != "999":
            itemname = f"{map_types[temp_ty]}-{index}"
            parsed.setdefault(itemname, float(reading_str) / 10)

    return parsed


def discover_stulz_temp(parsed):
    for item in parsed:
        yield item, {}


def check_stulz_temp(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item], params, "stulz_temp_%s" % item)
    return None


check_info["stulz_temp"] = LegacyCheckDefinition(
    name="stulz_temp",
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.1.1.1.1.1",
        oids=[OIDEnd(), "1"],
    ),
    parse_function=parse_stulz_temp,
    service_name="Temperature %s",
    discovery_function=discover_stulz_temp,
    check_function=check_stulz_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (25.0, 28.0)},
)
