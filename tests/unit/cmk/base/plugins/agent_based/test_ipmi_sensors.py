#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest

from cmk.base.plugins.agent_based import ipmi_sensors
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import ipmi as ipmi_utils

_STRING_TABLES = [
    [
        ["4  ", " CPU Temp       ", " Temperature ", " N/A       ", " C    ", " N/A"],
        ["71 ", " System Temp    ", " Temperature ", " N/A       ", " C    ", " N/A"],
        ["138 ", " Peripheral Temp ", " Temperature ", " N/A       ", " C    ", " N/A"],
        ["205 ", " PS1 Status     ", " Power Supply ", " N/A       ", " N/A  ", " N/A"],
        ["272 ", " PS2 Status     ", " Power Supply ", " N/A       ", " N/A  ", " N/A"],
    ],
    [
        ["4", "Temperature_CPU_Temp", "36.00_C_(0.00/100.00)", "[OK]"],
        ["71", "Temperature_System_Temp", "18.00_C_(-7.00/85.00)", "[OK]"],
        ["138", "Temperature_Peripheral_Temp", "27.00_C_(-7.00/85.00)", "[OK]"],
        ["942", "Voltage_Vcpu", "1.78_V_(1.26/2.09)", "[OK]"],
        ["1009", "Voltage_VDIMM", "1.46_V_(1.12/1.72)", "[OK]"],
        ["1076", "Voltage_12V", "11.95_V_(10.52/13.22)", "[OK]"],
        ["1478", "Physical_Security_Chassis_Intru", "[General_Chassis_Intrusion]"],
        ["1545", "Power_Supply_PS1_Status", "[Presence_detected]"],
        ["2081", "Power_Supply_PS2_Status", "[Presence_detected]"],
        ["4", "Temperature_CPU_Temp", "36.00_C_(0.00/100.00)", "[OK]"],
        ["339", "Temperature_DIMMA1_Temp", "22.00_C_(2.00/85.00)", "[OK]"],
        ["406", "Temperature_DIMMA2_Temp", "24.00_C_(2.00/85.00)", "[OK]"],
        ["607", "Fan_FAN1", "6800.00_RPM_(600.00/25400.00)", "[OK]"],
        ["674", "Fan_FAN2", "6700.00_RPM_(600.00/25400.00)", "[OK]"],
        ["942", "Voltage_Vcpu", "1.78_V_(1.26/2.09)", "[OK]"],
        ["1009", "Voltage_VDIMM", "1.46_V_(1.12/1.72)", "[OK]"],
        ["1478", "Physical_Security_Chassis_Intru", "[General_Chassis_Intrusion]"],
        ["1545", "Power_Supply_PS1_Status", "[Presence_detected]"],
        ["2081", "Power_Supply_PS2_Status", "[Presence_detected]"],
        ["4", "Temperature_CPU_Temp", "36.00_C_(0.00/100.00)", "[OK]"],
        ["71", "Temperature_System_Temp", "18.00_C_(-7.00/85.00)", "[OK]"],
        ["138", "Temperature_Peripheral_Temp", "27.00_C_(-7.00/85.00)", "[OK]"],
        ["607", "Fan_FAN1", "6800.00_RPM_(600.00/25400.00)", "[OK]"],
        ["674", "Fan_FAN2", "6700.00_RPM_(600.00/25400.00)", "[OK]"],
        ["942", "Voltage_Vcpu", "1.78_V_(1.26/2.09)", "[OK]"],
        ["1344", "Voltage_AVCC", "3.37_V_(2.49/3.60)", "[OK]"],
        ["1411", "Voltage_VSB", "3.30_V_(2.49/3.60)", "[OK]"],
        ["1478", "Physical_Security_Chassis_Intru", "[General_Chassis_Intrusion]"],
        ["1545", "Power_Supply_PS1_Status", "[Presence_detected]"],
        ["2081", "Power_Supply_PS2_Status", "[Presence_detected]"],
    ],
    [
        ["32", "Temperature_Ambient", "20.00_C_(1.00/42.00)", "[OK]"],
        ["416", "Temperature_DIMM-2A", "NA(NA/115.00)", "[Unknown]"],
        ["4288", "Power_Unit_PSU", "[Redundancy_Lost]"],
        ["138", "OEM_Reserved_CPU_Temp", "NA_NA_(NA/NA)", "[OEM_Event_=_0000h]"],
        ["875", "Power_Supply_PS_Status", "NA_NA_(NA/NA)", "[Presence_detected]"],
        ["1", "Temperature_Inlet_Temp", "21.00_C_(NA/48.00)", "[OK]"],
        ["59", "M2_Temp0(PCIe1)_(Temperature)", "NA/79.00_41.00_C", "[OK]"],
        ["20", "Fan_FAN1_F_Speed", "7200.00_RPM_(NA/NA)", "[OK]"],
        ["162", "01-Inlet Ambient", "Temperature", "24.00", "C", "OK"],
        ["171", "Intrusion", "Physical Security", "N/A", "", "OK"],
        ["172", "SysHealth_Stat", "Chassis", "N/A", "", "OK"],
        ["174", "UID", "UNKNOWN type 192", "N/A", "", "no state reported"],
        ["182", "Power Meter", "Other", "260.00", "W", "OK"],
        ["72", "Memory Status", "Memory", "N/A", "error", "OK"],
        ["187", "Megacell Status", "Battery", "N/A", "", "OK"],
        ["35", "CPU Utilization", "Processor", "68.00", "", "OK"],
    ],
]

_SECTIONS = [
    {},
    {
        "Fan_FAN1": ipmi_utils.Sensor(
            status_txt="OK",
            unit="RPM",
            value=6800.0,
            crit_low=600.0,
            warn_low=None,
            warn_high=None,
            crit_high=25400.0,
        ),
        "Fan_FAN2": ipmi_utils.Sensor(
            status_txt="OK",
            unit="RPM",
            value=6700.0,
            crit_low=600.0,
            warn_low=None,
            warn_high=None,
            crit_high=25400.0,
        ),
        "Physical_Security_Chassis_Intru": ipmi_utils.Sensor(
            status_txt="General Chassis Intrusion",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Power_Supply_PS1_Status": ipmi_utils.Sensor(
            status_txt="Presence detected",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Power_Supply_PS2_Status": ipmi_utils.Sensor(
            status_txt="Presence detected",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Temperature_CPU_Temp": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=36.0,
            crit_low=0.0,
            warn_low=None,
            warn_high=None,
            crit_high=100.0,
        ),
        "Temperature_DIMMA1_Temp": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=22.0,
            crit_low=2.0,
            warn_low=None,
            warn_high=None,
            crit_high=85.0,
        ),
        "Temperature_DIMMA2_Temp": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=24.0,
            crit_low=2.0,
            warn_low=None,
            warn_high=None,
            crit_high=85.0,
        ),
        "Temperature_Peripheral_Temp": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=27.0,
            crit_low=-7.0,
            warn_low=None,
            warn_high=None,
            crit_high=85.0,
        ),
        "Temperature_System_Temp": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=18.0,
            crit_low=-7.0,
            warn_low=None,
            warn_high=None,
            crit_high=85.0,
        ),
        "Voltage_12V": ipmi_utils.Sensor(
            status_txt="OK",
            unit="V",
            value=11.95,
            crit_low=10.52,
            warn_low=None,
            warn_high=None,
            crit_high=13.22,
        ),
        "Voltage_AVCC": ipmi_utils.Sensor(
            status_txt="OK",
            unit="V",
            value=3.37,
            crit_low=2.49,
            warn_low=None,
            warn_high=None,
            crit_high=3.6,
        ),
        "Voltage_VDIMM": ipmi_utils.Sensor(
            status_txt="OK",
            unit="V",
            value=1.46,
            crit_low=1.12,
            warn_low=None,
            warn_high=None,
            crit_high=1.72,
        ),
        "Voltage_VSB": ipmi_utils.Sensor(
            status_txt="OK",
            unit="V",
            value=3.3,
            crit_low=2.49,
            warn_low=None,
            warn_high=None,
            crit_high=3.6,
        ),
        "Voltage_Vcpu": ipmi_utils.Sensor(
            status_txt="OK",
            unit="V",
            value=1.78,
            crit_low=1.26,
            warn_low=None,
            warn_high=None,
            crit_high=2.09,
        ),
    },
    {
        "01-Inlet_Ambient": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=24.0,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "CPU_Utilization": ipmi_utils.Sensor(
            status_txt="OK",
            unit="",
            value=68.0,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Fan_FAN1_F_Speed": ipmi_utils.Sensor(
            status_txt="OK",
            unit="RPM",
            value=7200.0,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Intrusion": ipmi_utils.Sensor(
            status_txt="OK",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "M2_Temp0(PCIe1)_(Temperature)": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=41.0,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=79.0,
        ),
        "Megacell_Status": ipmi_utils.Sensor(
            status_txt="OK",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Memory_Status": ipmi_utils.Sensor(
            status_txt="OK",
            unit="error",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Power_Meter": ipmi_utils.Sensor(
            status_txt="OK",
            unit="W",
            value=260.0,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Power_Supply_PS_Status": ipmi_utils.Sensor(
            status_txt="Presence detected",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Power_Unit_PSU": ipmi_utils.Sensor(
            status_txt="Redundancy Lost",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "SysHealth_Stat": ipmi_utils.Sensor(
            status_txt="OK",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
        "Temperature_Ambient": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=20.0,
            crit_low=1.0,
            warn_low=None,
            warn_high=None,
            crit_high=42.0,
        ),
        "Temperature_Inlet_Temp": ipmi_utils.Sensor(
            status_txt="OK",
            unit="C",
            value=21.0,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=48.0,
        ),
        "UID": ipmi_utils.Sensor(
            status_txt="no state reported",
            unit="",
            value=None,
            crit_low=None,
            warn_low=None,
            warn_high=None,
            crit_high=None,
        ),
    },
]


@pytest.mark.parametrize(
    [
        "string_table",
        "expected_result",
    ],
    list(zip(_STRING_TABLES, _SECTIONS)),
)
def test_parse_ipmi_sensors(
    string_table: StringTable,
    expected_result: ipmi_utils.Section,
) -> None:
    assert ipmi_sensors.parse_ipmi_sensors(string_table) == expected_result


@pytest.mark.parametrize(
    [
        "section",
        "params",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTIONS[0],
            {
                "discovery_mode": ("single", {}),
            },
            [],
        ),
        pytest.param(
            _SECTIONS[1],
            {
                "discovery_mode": ("single", {}),
            },
            [
                Service(item="Fan_FAN1"),
                Service(item="Fan_FAN2"),
                Service(item="Physical_Security_Chassis_Intru"),
                Service(item="Power_Supply_PS1_Status"),
                Service(item="Power_Supply_PS2_Status"),
                Service(item="Temperature_CPU_Temp"),
                Service(item="Temperature_DIMMA1_Temp"),
                Service(item="Temperature_DIMMA2_Temp"),
                Service(item="Temperature_Peripheral_Temp"),
                Service(item="Temperature_System_Temp"),
                Service(item="Voltage_12V"),
                Service(item="Voltage_AVCC"),
                Service(item="Voltage_VDIMM"),
                Service(item="Voltage_VSB"),
                Service(item="Voltage_Vcpu"),
            ],
        ),
        pytest.param(
            _SECTIONS[2],
            {
                "discovery_mode": (
                    "single",
                    {
                        "ignored_sensors": ["UID", "Temperature_Inlet_Temp"],
                        "ignored_sensorstates": ["Redundancy Lost"],
                    },
                )
            },
            [
                Service(item="01-Inlet_Ambient"),
                Service(item="CPU_Utilization"),
                Service(item="Fan_FAN1_F_Speed"),
                Service(item="Intrusion"),
                Service(item="M2_Temp0(PCIe1)_(Temperature)"),
                Service(item="Megacell_Status"),
                Service(item="Memory_Status"),
                Service(item="Power_Meter"),
                Service(item="Power_Supply_PS_Status"),
                Service(item="SysHealth_Stat"),
                Service(item="Temperature_Ambient"),
            ],
        ),
        pytest.param(
            _SECTIONS[2],
            {"discovery_mode": (
                "summarize",
                {},
            )},
            [
                Service(item="Summary FreeIPMI"),
            ],
        ),
    ],
)
def test_discover_ipmi_sensors(
    section: ipmi_utils.Section,
    params: ipmi_utils.DiscoveryParams,
    expected_result: DiscoveryResult,
) -> None:
    assert (list(ipmi_sensors.discover_ipmi_sensors(
        params,
        section,
    )) == expected_result)


@pytest.mark.parametrize(
    [
        "item",
        "params",
        "section",
        "expected_result",
    ],
    [
        pytest.param(
            "Temperature_Inlet_Temp",
            {},
            _SECTIONS[2],
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="21.00 C"),
                Metric("value", 21.0, levels=(None, 48.0)),
            ],
        ),
        pytest.param(
            "Power_Supply_PS2_Status",
            {
                "sensor_states": [("Presence detected", 3),],
            },
            _SECTIONS[1],
            [
                Result(state=State.OK, summary="Status: Presence detected"),
                Result(state=State.UNKNOWN, summary="User-defined state"),
            ],
        ),
        pytest.param(
            "Voltage_AVCC",
            {
                "numerical_sensor_levels": [(
                    "Voltage_AVCC",
                    {
                        "upper": (1, 2),
                    },
                ),],
            },
            _SECTIONS[1],
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="3.37 V"),
                Result(state=State.CRIT,
                       summary="Voltage_AVCC: 3.37 V (warn/crit at 1.00 V/2.00 V)"),
            ],
        ),
    ],
)
def test_check_ipmi_sensors(
    item: str,
    params: Mapping[str, Any],
    section: ipmi_utils.Section,
    expected_result: CheckResult,
) -> None:
    assert (list(ipmi_sensors.check_ipmi_sensors(
        item,
        params,
        section,
    )) == expected_result)
