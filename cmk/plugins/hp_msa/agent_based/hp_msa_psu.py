#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

from .health import check_hp_msa_health, discover_hp_msa_health
from .lib import parse_hp_msa, Section

# <<<hp_msa_psu>>>
# power-supplies 1 durable-id psu_1.1
# power-supplies 1 enclosure-id 1
# power-supplies 1 serial-number 7CE451T700
# power-supplies 1 description FRU,Pwr Sply,595W,AC,2U,LC,HP
# power-supplies 1 name PSU 1, Left
# power-supplies 1 revision D1
# power-supplies 1 model 592267-002
# power-supplies 1 vendor 0x
# power-supplies 1 location Enclosure 1 - Left
# power-supplies 1 position Left
# power-supplies 1 position-numeric 0
# power-supplies 1 part-number 592267-002
# power-supplies 1 dash-level
# power-supplies 1 fru-shortname AC Power Supply
# power-supplies 1 mfg-date 2014-10-29 16:57:47
# power-supplies 1 mfg-date-numeric 1414601867
# power-supplies 1 mfg-location Zhongshan,Guangdong,CN
# power-supplies 1 mfg-vendor-id 0x
# power-supplies 1 configuration-serialnumber 7CE451T700
# power-supplies 1 dc12v 1195
# power-supplies 1 dc5v 508
# power-supplies 1 dc33v 336
# power-supplies 1 dc12i 548
# power-supplies 1 dc5i 489
# power-supplies 1 dctemp 34
# power-supplies 1 health OK
# power-supplies 1 health-numeric 0
# power-supplies 1 health-reason
# power-supplies 1 health-recommendation
# power-supplies 1 status Up
# power-supplies 1 status-numeric 0

#   .--health--------------------------------------------------------------.
#   |                    _                _ _   _                          |
#   |                   | |__   ___  __ _| | |_| |__                       |
#   |                   | '_ \ / _ \/ _` | | __| '_ \                      |
#   |                   | | | |  __/ (_| | | |_| | | |                     |
#   |                   |_| |_|\___|\__,_|_|\__|_| |_|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                            main check                                |
#   '----------------------------------------------------------------------'

agent_section_hp_msa_psu_health = AgentSection(
    name="hp_msa_psu",
    parse_function=parse_hp_msa,
)

check_plugin_hp_msa_psu_health = CheckPlugin(
    name="hp_msa_psu",
    service_name="Power Supply Health %s",
    discovery_function=discover_hp_msa_health,
    check_function=check_hp_msa_health,
)

# .
#   .--voltage-------------------------------------------------------------.
#   |                             _ _                                      |
#   |                 __   _____ | | |_ __ _  __ _  ___                    |
#   |                 \ \ / / _ \| | __/ _` |/ _` |/ _ \                   |
#   |                  \ V / (_) | | || (_| | (_| |  __/                   |
#   |                   \_/ \___/|_|\__\__,_|\__, |\___|                   |
#   |                                        |___/                         |
#   '----------------------------------------------------------------------'


def discover_hp_msa_psu(section: Section) -> DiscoveryResult:
    """detect if PSU info is invalid

    Some fields where deprecated for HP MSA 1050/2050.
    If the PSU is freezing and has no voltage we assume
    that means data is not valid
    """
    indicators = ("dc12v", "dc5v", "dc33v", "dc12i", "dc5i", "dctemp")
    for item, data in section.items():
        if any(data.get(i) != "0" for i in indicators):
            yield Service(item=item)


def check_hp_msa_psu(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    for psu_type, psu_type_readable, levels_type in [
        ("dc12v", "12 V", "levels_12v_"),
        ("dc5v", "5 V", "levels_5v_"),
        ("dc33v", "3.3 V", "levels_33v_"),
    ]:
        psu_voltage = float(data[psu_type]) / 100
        yield from check_levels_v1(
            psu_voltage,
            levels_lower=params[levels_type + "lower"],
            levels_upper=params[levels_type + "upper"],
            render_func=lambda x: f"{x:.2f} V",
            label=psu_type_readable,
        )


check_plugin_hp_msa_psu_sensor = CheckPlugin(
    name="hp_msa_psu_sensor",
    service_name="Power Supply Voltage %s",
    sections=["hp_msa_psu"],
    discovery_function=discover_hp_msa_psu,
    check_function=check_hp_msa_psu,
    check_ruleset_name="hp_msa_psu_voltage",
    check_default_parameters={
        "levels_33v_lower": (3.25, 3.20),
        "levels_33v_upper": (3.4, 3.45),
        "levels_5v_lower": (4.9, 4.8),
        "levels_5v_upper": (5.1, 5.2),
        "levels_12v_lower": (11.9, 11.8),
        "levels_12v_upper": (12.1, 12.2),
    },
)

# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+


def check_hp_msa_psu_temp(
    item: str,
    params: TempParamType,
    section: Section,
) -> CheckResult:
    yield from check_hp_msa_psu_temp_testable(item, params, section, get_value_store())


def check_hp_msa_psu_temp_testable(
    item: str,
    params: TempParamType,
    section: Section,
    value_store: MutableMapping[str, object],
) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from check_temperature(
        float(data["dctemp"]), params, value_store=value_store, unique_name=""
    )


check_plugin_hp_msa_psu_temp = CheckPlugin(
    name="hp_msa_psu_temp",
    service_name="Temperature Power Supply %s",
    sections=["hp_msa_psu"],
    discovery_function=discover_hp_msa_psu,
    check_function=check_hp_msa_psu_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 45.0),  # Just assumed
    },
)
