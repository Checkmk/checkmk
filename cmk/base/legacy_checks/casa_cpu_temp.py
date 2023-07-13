#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.casa import DETECT_CASA


def parse_casa_info_temp(info):
    entity_names = {int(k): v for k, v in (x for x in info[0])}
    temp_value = {int(k): v for k, v in (x for x in info[1])}
    temp_status = {int(k): v for k, v in (x for x in info[2])}
    temp_unit = {int(k): v for k, v in (x for x in info[3])}
    data = {}
    for entry in info[1]:
        entry_nr = int(entry[0])

        def beautify_module_text(text):
            text = text.replace("temperature sensor", "")
            if text.startswith("Module "):
                text = text.rsplit(None, 1)[0]  # Drop trailing " CPU"
            return text

        data[beautify_module_text(entity_names[entry_nr])] = {
            "temp_value": temp_value.get(entry_nr),
            "temp_status": temp_status.get(entry_nr),
            "temp_unit": temp_unit.get(entry_nr),
        }
    return data


def inventory_casa_cpu_temp(parsed):
    for key, value in parsed.items():
        if value.get("temp_value"):
            yield key, None


def check_casa_cpu_temp(item, params, parsed):
    if item in parsed:
        if parsed[item]["temp_status"] == "1":
            value = float(parsed[item]["temp_value"]) / 10
            return check_temperature(value, params, "case_cpu_temp_%s" % item)
        return (2, "Sensor failure!", [])
    return None


check_info["casa_cpu_temp"] = LegacyCheckDefinition(
    detect=DETECT_CASA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.99.1.1.1",
            oids=[OIDEnd(), "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.99.1.1.1",
            oids=[OIDEnd(), "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.99.1.1.1",
            oids=[OIDEnd(), "6"],
        ),
    ],
    parse_function=parse_casa_info_temp,
    service_name="Temperature CPU %s",
    discovery_function=inventory_casa_cpu_temp,
    check_function=check_casa_cpu_temp,
    check_ruleset_name="temperature",
)
