#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature_list
from cmk.plugins.lib.intel import DETECT_INTEL_TRUE_SCALE

check_info = {}

# mypy: disable-error-code="var-annotated"


# .1.3.6.1.4.1.10222.2.1.2.9.1.1.1.1.1 1 --> ICS-CHASSIS-MIB::icsChassisSlotIndex.1.1.1
# .1.3.6.1.4.1.10222.2.1.2.9.1.1.1.2.1 2 --> ICS-CHASSIS-MIB::icsChassisSlotIndex.1.2.1
#
# .1.3.6.1.4.1.10222.2.1.9.8.1.2.1.1.1 2 --> ICS-CHASSIS-MIB::icsChassisSensorSlotType.1.1.1
# .1.3.6.1.4.1.10222.2.1.9.8.1.2.1.1.2 2 --> ICS-CHASSIS-MIB::icsChassisSensorSlotType.1.1.2
# .1.3.6.1.4.1.10222.2.1.9.8.1.2.1.2.1 2 --> ICS-CHASSIS-MIB::icsChassisSensorSlotType.1.2.1
# .1.3.6.1.4.1.10222.2.1.9.8.1.2.1.2.2 2 --> ICS-CHASSIS-MIB::icsChassisSensorSlotType.1.2.2
# .1.3.6.1.4.1.10222.2.1.9.8.1.3.1.1.1 4 --> ICS-CHASSIS-MIB::icsChassisSensorSlotOperStatus.1.1.1
# .1.3.6.1.4.1.10222.2.1.9.8.1.3.1.1.2 4 --> ICS-CHASSIS-MIB::icsChassisSensorSlotOperStatus.1.1.2
# .1.3.6.1.4.1.10222.2.1.9.8.1.3.1.2.1 4 --> ICS-CHASSIS-MIB::icsChassisSensorSlotOperStatus.1.2.1
# .1.3.6.1.4.1.10222.2.1.9.8.1.3.1.2.2 4 --> ICS-CHASSIS-MIB::icsChassisSensorSlotOperStatus.1.2.2
# .1.3.6.1.4.1.10222.2.1.9.8.1.7.1.1.1  FUSION -- baseboard temp --> ICS-CHASSIS-MIB::icsChassisSensorSlotDescription.1.1.1
# .1.3.6.1.4.1.10222.2.1.9.8.1.7.1.1.2  FUSION -- fusion temp --> ICS-CHASSIS-MIB::icsChassisSensorSlotDescription.1.1.2
# .1.3.6.1.4.1.10222.2.1.9.8.1.7.1.2.1  FUSION -- baseboard temp --> ICS-CHASSIS-MIB::icsChassisSensorSlotDescription.1.2.1
# .1.3.6.1.4.1.10222.2.1.9.8.1.7.1.2.2  FUSION -- fusion temp --> ICS-CHASSIS-MIB::icsChassisSensorSlotDescription.1.2.2
# .1.3.6.1.4.1.10222.2.1.9.8.1.8.1.1.1 41 --> ICS-CHASSIS-MIB::icsChassisSensorSlotValue.1.1.1
# .1.3.6.1.4.1.10222.2.1.9.8.1.8.1.1.2 32 --> ICS-CHASSIS-MIB::icsChassisSensorSlotValue.1.1.2
# .1.3.6.1.4.1.10222.2.1.9.8.1.8.1.2.1 49 --> ICS-CHASSIS-MIB::icsChassisSensorSlotValue.1.2.1
# .1.3.6.1.4.1.10222.2.1.9.8.1.8.1.2.2 31 --> ICS-CHASSIS-MIB::icsChassisSensorSlotValue.1.2.2


def parse_intel_true_scale_sensors(string_table):
    map_slot_types = {
        "0": "unspecified",
        "1": "switch master",
        "2": "switch slave",
        "3": "eiou",
        "4": "fciou",
        "5": "other",
        "6": "spine master",
        "7": "spine slave",
        "8": "spine",
        "9": "leaf",
        "10": "viofx",
        "11": "vioex",
        "12": "shuttle master",
        "13": "shuttle slave",
        "14": "xMM master",
        "15": "xMM slave",
        "16": "xspine",
        "17": "xQleaf",
        "18": "xDleaf",
        "19": "xVioFx",
        "20": "xVioEx",
    }

    map_sensor_types = {
        "1": "other",
        "2": "temp",
        "3": "fan",
        "4": "humid",
        "5": "acpower",
        "6": "dcpower",
        "7": "slot",
        "8": "fuse",
    }

    map_states = {
        "0": (2, "invalid"),
        "1": (3, "unknown"),
        "2": (2, "bad"),
        "3": (1, "warning"),
        "4": (0, "good"),
        "5": (3, "disabled"),
    }

    slots, sensors = string_table
    parsed = {}
    for slot_id, slot_ty in slots:
        parsed.setdefault("slot %s" % slot_id, {"slot_type": map_slot_types[slot_ty]})

    for oid_end, ty, status, descr, reading_str in sensors:
        slot_id, sensor_id = oid_end.split(".")[1:]
        slot_name = "slot %s" % slot_id
        sensor_name = " ".join(descr.split(" ")[2:-1])

        # We do not known for all sensors. Feel free to extend
        if ty in ["5", "6"]:
            factor = 0.001
        else:
            factor = 1

        state, state_readable = map_states[status]
        kwargs = {"dev_status": state, "dev_status_name": state_readable}

        sensor_ty = map_sensor_types[ty]
        parsed[slot_name].setdefault(sensor_ty, [])
        parsed[slot_name][sensor_ty].append(
            (f"{sensor_id} {sensor_name}", float(reading_str) * factor, kwargs)
        )

    return parsed


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                            main check                                |
#   '----------------------------------------------------------------------'


def inventory_intel_true_scale_sensors_temp(parsed):
    for slot_name, slot_info in parsed.items():
        if slot_info.get("temp"):
            yield slot_name, {}


def check_intel_true_scale_sensors_temp(item, params, parsed):
    if item in parsed:
        yield from check_temperature_list(parsed[item]["temp"], params)


check_info["intel_true_scale_sensors_temp"] = LegacyCheckDefinition(
    name="intel_true_scale_sensors_temp",
    detect=DETECT_INTEL_TRUE_SCALE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.10222.2.1.2.9.1",
            oids=["1", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.10222.2.1.9.8.1",
            oids=[OIDEnd(), "2", "3", "7", "8"],
        ),
    ],
    parse_function=parse_intel_true_scale_sensors,
    service_name="Temperature sensors %s",
    discovery_function=inventory_intel_true_scale_sensors_temp,
    check_function=check_intel_true_scale_sensors_temp,
)
