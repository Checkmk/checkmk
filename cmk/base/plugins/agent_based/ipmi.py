#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs
from .utils import ipmi

# Example of output from ipmi:
# <<<ipmi>>>
# ambienttemp 25.800 degrees_C ok na na na 34.800 40.200 na
# bulk.v12-0-s0 11.940 Volts ok na 10.200 na na 13.800 na
# bulk.v3_3-s0 3.360 Volts ok na 3.000 na na 3.600 na
# bulk.v3_3-s5 3.240 Volts ok na 3.000 na na 3.600 na
# bulk.v5-s0 5.040 Volts ok na 4.500 na na 5.520 na
# bulk.v5-s5 5.040 Volts ok na 4.500 na na 5.520 na
# cpu0.dietemp 51.000 degrees_C ok na na na 70.200 73.200 na
# ...
# On another host
# mb.t_amb 24.000 degrees_C ok na na na 70.000 75.000 80.000
# mb.v_bat 2.839 Volts ok 2.340 2.527 2.621 3.307 3.510 3.697
# mb.v_+3v3stby 3.218 Volts ok 2.595 2.785 2.993 3.598 3.789 3.996
# mb.v_+3v3 3.339 Volts ok 2.595 2.785 2.993 3.598 3.789 3.996
# mb.v_+5v 5.044 Volts ok 3.484 3.978 4.498 5.486 5.980 6.500
# fp.t_amb 21.000 degrees_C ok na na na 30.000 35.000 45.000
# pdb.t_amb 21.000 degrees_C ok na na na 70.000 75.000 80.000
# io.t_amb 19.000 degrees_C ok na na na 70.000 75.000 80.000
# p0.t_core 18.000 degrees_C ok na na na 62.000 67.000 75.000
# p0.v_vdd 1.332 Volts ok 0.792 0.900 0.996 1.596 1.692 1.800

# Yet another host (HP DL 360G5)
# <<<ipmi>>>
# UID_Light 0.000 unspecified ok na na 0.000 na na na
# Int._Health_LED 0.000 unspecified ok na na 0.000 na na na
# Ext._Health_LED 0.000 unspecified ok na na 0.000 na na na
# Power_Supply_1 0.000 unspecified nc na na 0.000 na na na
# Power_Supply_2 0.000 unspecified nc na na 0.000 na na na
# Power_Supplies 0.000 unspecified nc na na 0.000 na na na
# VRM_1 0.000 unspecified cr na na 0.000 na na na
# VRM_2 0.000 unspecified cr na na 0.000 na na na
# Fan_Block_1 34.888 unspecified nc na na 75.264 na na na
# Fan_Block_2 29.792 unspecified nc na na 75.264 na na na
# Fan_Block_3 34.888 unspecified nc na na 75.264 na na na
# Fan_Blocks 0.000 unspecified nc na na 0.000 na na na
# Temp_1 39.000 degrees_C ok na na -64.000 na na na
# Temp_2 16.000 degrees_C ok na na -64.000 na na na
# Temp_3 30.000 degrees_C ok na na -64.000 na na na
# Temp_4 30.000 degrees_C ok na na -64.000 na na na
# Temp_5 25.000 degrees_C ok na na -64.000 na na na
# Temp_6 30.000 degrees_C ok na na -64.000 na na na
# Temp_7 30.000 degrees_C ok na na -64.000 na na na
# Power_Meter 180.000 Watts cr na na 384.000 na na na

# And this host has some false-criticals (PowerMeter, VirtualFan)
# <<<ipmi>>>
# Temp_1 17.000 degrees_C ok 0.000 0.000 0.000 40.000 42.000 46.000
# Temp_2 40.000 degrees_C ok 0.000 0.000 0.000 0.000 82.000 83.000
# Temp_3 44.000 degrees_C ok 0.000 0.000 0.000 0.000 82.000 83.000
# Temp_4 52.000 degrees_C ok 0.000 0.000 0.000 0.000 87.000 92.000
# Temp_5 46.000 degrees_C ok 0.000 0.000 0.000 0.000 85.000 90.000
# Temp_6 55.000 degrees_C ok 0.000 0.000 0.000 0.000 85.000 90.000
# Temp_7 51.000 degrees_C ok 0.000 0.000 0.000 0.000 85.000 90.000
# Temp_8 58.000 degrees_C ok 0.000 0.000 0.000 0.000 78.000 83.000
# Temp_9 74.000 degrees_C ok 0.000 0.000 0.000 0.000 110.000 115.000
# Temp_10 31.000 degrees_C ok 0.000 0.000 0.000 0.000 60.000 65.000
# Virtual_Fan 19.600 unspecified nc na na na na na na
# Power_Meter 236.000 Watts cr na na na na na na

# IPMI has two operation modes:
# 1. detailed
# 2. summarized
# This controls how the inventory is done. In summary-mode, the
# inventory returns one single check item 'Summary' - or nothing
# if the host does not send any IPMI information
# In Detailed mode for each sensor one item is returned.

# Newer output formats (sensor list and compact/discrete sensors)
# <<<ipmi:sep(124)>>>
# BB +5V           | 5.070      | Volts      | ok    | na        | 4.446     | 4.576     | 5.408     | 5.564     | na
# BB +12V AUX      | 11.904     | Volts      | ok    | na        | 10.416    | 10.726    | 13.144    | 13.578    | na
# BB +0.9V         | 0.898      | Volts      | ok    | na        | 0.811     | 0.835     | 0.950     | 0.979     | na
# Serverboard Temp | 39.000     | degrees C  | ok    | na        | 5.000     | 10.000    | 61.000    | 66.000    | na
# Ctrl Panel Temp  | 31.000     | degrees C  | ok    | na        | 0.000     | 5.000     | 44.000    | 48.000    | na
# Fan 1            | 7740.000   | RPM        | ok    | na        | 1720.000  | 1978.000  | na        | na        | na
# Fan 2            | 8557.000   | RPM        | ok    | na        | 1720.000  | 1978.000  | na        | na        | na
# Fan 3            | 7611.000   | RPM        | ok    | na        | 1720.000  | 1978.000  | na        | na        | na
# <<<ipmi_discrete:sep(124)>>>
# PS3 Status       | C8h | ok | 10.1 | Presence detected
# PS4 Status       | C9h | ok | 10.2 | Presence detected
# Pwr Unit Stat    | 01h | ok | 21.1 |
# Power Redundancy | 02h | ok | 21.1 | Fully Redundant
# BMC Watchdog     | 03h | ok |  7.1 |
# PS1 Status       | C8h | ok | 10.1 | Presence detected, Failure detected     <= NOT OK !!
# PS2 Status       | C9h | ok | 10.2 | Presence detected
# Drive 4          | 64h | ok  |  4.4 | Drive Present, Drive Fault <= NOT OK

# broken
# <<<ipmi:cached(1472175405,300)>>>
# 01-Inlet_Ambient 18.000 degrees_C ok na na na na 42.000 46.000
# 02-CPU_1 40.000 degrees_C ok na na na na 70.000 na
# 03-CPU_2 40.000 degrees_C ok na na na na 70.000 na
# 04-DIMM_P1_1-3 32.000 degrees_C ok na na na na 87.000 na
# 05-DIMM_P1_4-6 32.000 degrees_C ok na na na na 87.000 na
# 06-DIMM_P2_1-3 27.000 degrees_C ok na na na na 87.000 na
# 07-DIMM_P2_4-6 26.000 degrees_C ok na na na na 87.000 na
# 09-Chipset 47.000 degrees_C ok na na na na 105.000 na
# 10-VR_P1 32.000 degrees_C ok na na na na 115.000 120.000
# 11-VR_P2 27.000 degrees_C ok na na na na 115.000 120.000
# 12-VR_P1_Zone 27.000 degrees_C ok na na na na 80.000 85.000
# 13-VR_P2_Zone 25.000 degrees_C ok na na na na 80.000 85.000
# 14-VR_P1_Mem 33.000 degrees_C ok na na na na 115.000 120.000
# 15-VR_P2_Mem 23.000 degrees_C ok na na na na 115.000 120.000
# 16-VR_P1Mem_Zone 32.000 degrees_C ok na na na na 80.000 85.000
# 17-VR_P2Mem_Zone 22.000 degrees_C ok na na na na 80.000 85.000
# 18-HD_Controller 57.000 degrees_C ok na na na na 90.000 na
# 19-Supercap 32.000 degrees_C ok na na na na 65.000 na
# 21-PCI_Zone 30.000 degrees_C ok na na na na 80.000 85.000
# 23-I/O_1_Zone 28.000 degrees_C ok na na na na 80.000 85.000
# 26-I/O_LOM 40.000 degrees_C ok na na na na 100.000 na
# 27-Sys_Exhaust 31.000 degrees_C ok na na na na 80.000 85.000
# PS3_Inpu


def parse_ipmi(string_table: type_defs.StringTable) -> ipmi.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_ipmi([
    ... ['Ambient', '18.500', 'degrees_C', 'ok', 'na', '1.000', '6.000', '37.000', '42.000', 'na'],
    ... ['CPU', '33.000', 'degrees_C', 'ok', 'na', 'na', 'na', '95.000', '99.000', 'na'],
    ... ['PCH_1.05V', '1.040', 'Volts', 'ok', 'na', '0.970', 'na', 'na', '1.130', 'na'],
    ... ['Total_Power', '48.000', 'Watts', 'ok', 'na', 'na', 'na', 'na', '498.000', 'na'],
    ... ['I2C4_error_ratio', '0.000', 'percent', 'ok', 'na', 'na', 'na', '10.000', '20.000', 'na'],
    ... ]))
    {'Ambient': Sensor(status_txt='ok', unit='degrees_C', value=18.5, crit_low=1.0, warn_low=6.0, warn_high=37.0, crit_high=42.0),
     'CPU': Sensor(status_txt='ok', unit='degrees_C', value=33.0, crit_low=None, warn_low=None, warn_high=95.0, crit_high=99.0),
     'I2C4_error_ratio': Sensor(status_txt='ok', unit='percent', value=0.0, crit_low=None, warn_low=None, warn_high=10.0, crit_high=20.0),
     'PCH_1.05V': Sensor(status_txt='ok', unit='Volts', value=1.04, crit_low=0.97, warn_low=None, warn_high=None, crit_high=1.13),
     'Total_Power': Sensor(status_txt='ok', unit='Watts', value=48.0, crit_low=None, warn_low=None, warn_high=None, crit_high=498.0)}
    >>> pprint(parse_ipmi([
    ... ['CMOS Battery     ', ' 10h ', ' ok  ', '  7.1 ', ''],
    ... ['VCORE            ', ' 12h ', ' ok  ', '  3.1 ', ' State Deasserted'],
    ... ['MSR Info Log     ', ' 28h ', ' ns  ', ' 34.1 ', ' No Reading'],
    ... ['Power Redundancy ', ' 02h ', ' ok ', ' 21.1 ', ' Fully Redundant'],
    ... ['PS1 Status       ', ' C8h ', ' ok ', ' 10.1 ', ' Presence detected, Failure detected     <= NOT OK !!'],
    ... ]))
    {'CMOS_Battery': Sensor(status_txt='ok', unit='', value=None, crit_low=None, warn_low=None, warn_high=None, crit_high=None),
     'MSR_Info_Log': Sensor(status_txt='ns (No Reading)', unit='', value=None, crit_low=None, warn_low=None, warn_high=None, crit_high=None),
     'PS1_Status': Sensor(status_txt='ok (Presence detected, Failure detected     <= NOT OK !!)', unit='', value=None, crit_low=None, warn_low=None, warn_high=None, crit_high=None),
     'Power_Redundancy': Sensor(status_txt='ok (Fully Redundant)', unit='', value=None, crit_low=None, warn_low=None, warn_high=None, crit_high=None),
     'VCORE': Sensor(status_txt='ok (State Deasserted)', unit='', value=None, crit_low=None, warn_low=None, warn_high=None, crit_high=None)}
    """
    parsed: ipmi.Section = {}
    for line in string_table:
        if len(line) >= 2:
            # Compatible with older check versions
            name = line[0].strip().replace(" ", "_")
            line = [name] + [x.strip() for x in line[1:]]

            # Discrete sensors have no values
            if len(line) == 5:
                status = line[2]
                if line[4]:
                    status += " (%s)" % line[4]
                line = [line[0], "", "", status, "", "", "", "", "", ""]

        if len(line) == 10:
            data = dict(
                zip(
                    [
                        "value",
                        "unit",
                        "status_txt",
                        "unrec_low",
                        "crit_low",
                        "warn_low",
                        "warn_high",
                        "crit_high",
                        "unrec_high",
                    ],
                    line[1:],
                )
            )

            sensor = parsed.setdefault(
                name,
                ipmi.Sensor(
                    data["status_txt"],
                    data["unit"].replace(" ", "_"),
                ),
            )

            # For each entry either we have valid value or None
            for what in ["value", "crit_low", "warn_low", "warn_high", "crit_high"]:
                try:
                    setattr(
                        sensor,
                        what,
                        float(data[what]),
                    )
                except ValueError:
                    continue

    return parsed


register.agent_section(
    name="ipmi",
    parse_function=parse_ipmi,
)

register.agent_section(
    name="ipmi_discrete",
    parse_function=parse_ipmi,
)


def _merge_sections(
    section_ipmi: Optional[ipmi.Section],
    section_ipmi_discrete: Optional[ipmi.Section],
) -> ipmi.Section:
    return {
        **(section_ipmi_discrete or {}),
        **(section_ipmi or {}),
    }


def discover_ipmi(
    params: ipmi.DiscoveryParams,
    section_ipmi: Optional[ipmi.Section],
    section_ipmi_discrete: Optional[ipmi.Section],
) -> type_defs.DiscoveryResult:
    section_merged = _merge_sections(section_ipmi, section_ipmi_discrete)

    mode, ignore_params = params["discovery_mode"]
    if mode == "summarize":
        yield Service(item="Summary")
        return

    ignore_params = {
        "ignored_sensorstates": ["ns", "nr", "na"],
        **ignore_params,
    }
    for sensor_name, sensor in section_merged.items():
        if not ipmi.ignore_sensor(sensor_name, sensor.status_txt, ignore_params):
            yield Service(item=sensor_name)


def ipmi_status_txt_mapping(status_txt: str) -> state:
    status_txt_lower = status_txt.lower()
    if status_txt.startswith("ok") and not (
        "failure detected" in status_txt_lower
        or "in critical array" in status_txt_lower
        or "drive fault" in status_txt_lower
    ):
        return state.OK
    if status_txt.startswith("nc"):
        return state.WARN
    return state.CRIT


def check_ipmi(
    item: str,
    params: Mapping[str, Any],
    section_ipmi: Optional[ipmi.Section],
    section_ipmi_discrete: Optional[ipmi.Section],
) -> type_defs.CheckResult:
    yield from ipmi.check_ipmi(
        item,
        params,
        _merge_sections(section_ipmi, section_ipmi_discrete),
        False,
        ipmi_status_txt_mapping,
    )


register.check_plugin(
    name="ipmi",
    sections=["ipmi", "ipmi_discrete"],
    service_name="IPMI Sensor %s",
    discovery_function=discover_ipmi,
    discovery_ruleset_name="inventory_ipmi_rules",
    discovery_default_parameters={"discovery_mode": ("summarize", {})},
    check_function=check_ipmi,
    check_ruleset_name="ipmi",
    check_default_parameters={"ignored_sensorstates": ["ns", "nr", "na"]},
)
