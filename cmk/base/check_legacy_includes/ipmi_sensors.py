#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file

from cmk.base.check_api import host_extra_conf, host_name

from .ipmi_common import check_ipmi_common, ipmi_ignore_entry

#   .--output--------------------------------------------------------------.
#   |                               _               _                      |
#   |                    ___  _   _| |_ _ __  _   _| |_                    |
#   |                   / _ \| | | | __| '_ \| | | | __|                   |
#   |                  | (_) | |_| | |_| |_) | |_| | |_                    |
#   |                   \___/ \__,_|\__| .__/ \__,_|\__|                   |
#   |                                  |_|                                 |
#   '----------------------------------------------------------------------'

# Old output format from agent and special agent
# <<<ipmi_sensors>>>
# 32 Temperature_Ambient 20.00_C_(1.00/42.00) [OK]
# 96 Temperature_Systemboard 23.00_C_(1.00/65.00) [OK]
# 160 Temperature_CPU_1 31.00_C_(1.00/90.00) [OK]
# 224 Temperature_CPU_2 NA(1.00/78.00) [Unknown]
# 288 Temperature_DIMM-1A 54.00_C_(NA/115.00) [OK]
# 352 Temperature_DIMM-1B 56.00_C_(NA/115.00) [OK]
# 416 Temperature_DIMM-2A NA(NA/115.00) [Unknown]
# 480 Temperature_DIMM-2B NA(NA/115.00) [Unknown]
# 544 Temperature_DIMM-3A NA(NA/115.00) [Unknown]
# 608 Temperature_DIMM-3B NA(NA/115.00) [Unknown]
# 672 Temperature_DIMM-4A NA(NA/NA) [Unknown]
# 736 Temperature_DIMM-4B NA(NA/NA) [Unknown]
# 800 Temperature_DIMM-1C NA(NA/115.00) [Unknown]
# 864 Temperature_DIMM-1D NA(NA/115.00) [Unknown]
# 928 Temperature_DIMM-2C NA(NA/115.00) [Unknown]
# 992 Temperature_DIMM-2D NA(NA/115.00) [Unknown]
# 1056 Temperature_DIMM-3C NA(NA/115.00) [Unknown]
# 1120 Temperature_DIMM-3D NA(NA/115.00) [Unknown]
# 1184 Temperature_DIMM-4C NA(NA/NA) [Unknown]
# 1248 Temperature_DIMM-4D NA(NA/NA) [Unknown]
# 4288 Power_Unit_PSU [Redundancy_Lost]
# 4336 Power_Unit_PSU [Unknown]
# 3104 Fan_FAN1_CPU 3600.00_RPM_(1800.00/NA) [OK]
# 3168 Fan_FAN2_CPU 3600.00_RPM_(1800.00/NA) [OK]
# 3232 Fan_FAN3_CPU 3540.00_RPM_(1800.00/NA) [OK]
# 3296 Fan_FAN4_CPU NA(1800.00/NA) [Unknown]
# 3360 Fan_FAN5_CPU NA(1800.00/NA) [Unknown]
# 3424 Fan_FAN6_CPU NA(1800.00/NA) [Unknown]
# 3488 Fan_FAN1_SYS 3360.00_RPM_(1800.00/NA) [OK]
# 3552 Fan_FAN2_SYS NA(1800.00/NA) [Unknown]
# 3616 Fan_FAN_PSU1 6840.00_RPM_(2760.00/NA) [OK]
# 3680 Fan_FAN_PSU2 0.00_RPM_(2760.00/NA) [OK]

# <<<ipmi_sensors>>>
# 4 Temperature_System_Temp 23.00_C_(NA/NA) [OK]
# 71 Temperature_Peripheral_Temp 29.00_C_(NA/NA) [OK]
# 138 OEM_Reserved_CPU_Temp NA_NA_(NA/NA) [OEM_Event_=_0000h] <= unknown sensor state, we do not discover
# 205 Fan_FAN 3225.00_RPM_(NA/NA) [OK]
# 272 Voltage_Vcore 0.68_V_(NA/NA) [OK]
# 339 Voltage_3.3VCC 3.33_V_(NA/NA) [OK]
# 406 Voltage_12V 12.08_V_(NA/NA) [OK]
# 473 Voltage_VDIMM 1.50_V_(NA/NA) [OK]
# 540 Voltage_5VCC 5.12_V_(NA/NA) [OK]
# 607 Voltage_VCC_PCH 1.06_V_(NA/NA) [OK]
# 674 Voltage_VBAT 3.17_V_(NA/NA) [OK]
# 741 Voltage_VSB 3.33_V_(NA/NA) [OK]
# 808 Voltage_AVCC 3.33_V_(NA/NA) [OK]
# 875 Power_Supply_PS_Status NA_NA_(NA/NA) [Presence_detected]

# Newer output format
# <<<ipmi_sensors:sep(124)>>>
# ID   | Name            | Type              | Reading    | Units | Event
# 4    | CPU Temp        | Temperature       | 28.00      | C     | 'OK'
# 71   | System Temp     | Temperature       | 28.00      | C     | 'OK'
# 607  | P1-DIMMC2 TEMP  | Temperature       | N/A        | C     | N/A

# unr: Upper Non-Recoverable
# ucr: Upper Critical
# unc: Upper Non-Critical
# lnc: Lower Non-Critical
# lcr: Lower Critical
# lnr: Lower Non-Recoverable
# <<<ipmi_sensors:sep(124)>>>
# ID | Name            | Type         | State    | Reading    | Units | Lower NR   | Lower C    | Lower NC   | Upper NC   | Upper C    | Upper NR   | Event
# 0  | UID Light       | OEM Reserved | N/A      | N/A        | N/A   | N/A        | N/A        | N/A        | N/A        | N/A        | N/A        | 'OK'
# 1  | Sys. Health LED | OEM Reserved | N/A      | N/A        | N/A   | N/A        | N/A        | N/A        | N/A        | N/A        | N/A        | 'OK'
# 2  | Power Supply 1  | Power Supply | Nominal  | N/A        | N/A   | N/A        | N/A        | N/A        | N/A        | N/A        | N/A        | 'Presence detected'
# 3  | Power Supply 2  | Power Supply | Nominal  | N/A        | N/A   | N/A        | N/A        | N/A        | N/A        | N/A        | N/A        | 'Presence detected'
# 4  | Power Supplies  | Power Supply | Nominal  | N/A        | N/A   | N/A        | N/A        | N/A        | N/A        | N/A        | N/A        | 'Fully Redundant'

#.


def parse_freeipmi(info):
    def add_valid_values(values):
        for key, value, ty in values:
            if value not in ["NA", "N/A"]:
                instance[key] = ty(value)

    parsed = {}
    for line in info:
        stripped_line = [x.strip(u' \n\t\x00') for x in line]
        status_txt = stripped_line[-1]
        if status_txt.startswith("[") or status_txt.startswith("'"):
            status_txt = status_txt[1:]
        if status_txt.endswith("]") or status_txt.endswith("'"):
            status_txt = status_txt[:-1]
        if status_txt in ["NA", "N/A", "Unknown"] or "_=_" in status_txt:
            status_txt = None
        elif status_txt in ["S0G0", "S0/G0"]:
            status_txt = "System full operational, working"
        else:
            status_txt = status_txt.replace("_", " ")

        sensorname = stripped_line[1].replace(" ", "_")
        instance = parsed.setdefault(
            sensorname, {
                "value": None,
                "unit": None,
                "status_txt": status_txt,
                "unrec_low": None,
                "crit_low": None,
                "warn_low": None,
                "warn_high": None,
                "crit_high": None,
                "unrec_high": None,
            })

        if len(stripped_line) == 4:
            if "(" in stripped_line[2]:
                # 339 Voltage_3.3VCC 3.33_V_(NA/NA) [OK]
                current, levels = stripped_line[2].split("(")
                lower, upper = levels[:-1].split("/")
            else:
                # 59 M2_Temp0(PCIe1)_(Temperature) NA/79.00_41.00_C [OK]
                levels, current = stripped_line[2].split("_", 1)
                lower, upper = levels.split("/")
            cparts = current.split("_")
            unit = "NA"
            if len(cparts) > 1:
                unit = cparts[1]

            add_valid_values([("value", cparts[0], float), ("unit", unit, str),
                              ("crit_low", lower, float), ("crit_high", upper, float)])

        elif len(stripped_line) == 6:
            _sid, _name, _sensortype, reading_str, unit = stripped_line[:-1]
            add_valid_values([("value", reading_str, float), ("unit", unit, str)])

        elif len(stripped_line) == 13:
            _sid, _name, _stype, _sstate, reading_str, unit, _lower_nr, lower_c, \
                lower_nc, upper_nc, upper_c, _upper_nr = stripped_line[:-1]
            add_valid_values([("value", reading_str, float), ("unit", unit, str),
                              ("crit_low", lower_c, float), ("warn_low", lower_nc, float),
                              ("warn_high", upper_nc, float), ("crit_high", upper_c, float)])

    return parsed


inventory_ipmi_rules = []


def inventory_freeipmi(parsed):
    rules = host_extra_conf(host_name(), inventory_ipmi_rules)
    if rules:
        mode, ignore_params = rules[0]["discovery_mode"]
    else:
        mode, ignore_params = 'single', {}

    if mode == "summarize":
        yield "Summary FreeIPMI", {}
    else:
        for sensorname, data in parsed.items():
            if not ipmi_ignore_entry(sensorname, data["status_txt"], ignore_params):
                yield sensorname, {}


def freeipmi_status_txt_mapping(status_txt):
    if status_txt is None:
        return 3

    state = {
        "ok": 0,
        "warning": 1,
        "critical": 2,
        "failed": 2,
        "unknown": 3,
    }.get(status_txt.lower())
    if state is not None:
        return state

    if "non-critical" in status_txt.lower():
        return 1

    if status_txt.lower() in [
        "entity present", "battery presence detected",
        "drive presence", "transition to running", "device enabled",
        "system full operational, working", "system restart", "present",
        "transition to ok",
        ] or \
       status_txt.startswith("Fully Redundant") or \
       status_txt.endswith("is connected") or \
       status_txt.endswith("Presence detected") or \
       status_txt.endswith("Device Present"):
        return 0
    return 2


def check_freeipmi(item, params, parsed):
    return check_ipmi_common(item, params, parsed, "freeipmi", freeipmi_status_txt_mapping)
