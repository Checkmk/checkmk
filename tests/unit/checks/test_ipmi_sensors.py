#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

import pytest
from pytest_mock import MockerFixture

from testlib import Check

from checktestlib import MockHostExtraConf

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based import register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

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
    {
        "CPU_Temp": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": None,
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "PS1_Status": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": None,
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "PS2_Status": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": None,
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Peripheral_Temp": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": None,
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "System_Temp": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": None,
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
    },
    {
        "Fan_FAN1": {
            "crit_high": 25400.0,
            "crit_low": 600.0,
            "status_txt": "OK",
            "unit": "RPM",
            "unrec_high": None,
            "unrec_low": None,
            "value": 6800.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Fan_FAN2": {
            "crit_high": 25400.0,
            "crit_low": 600.0,
            "status_txt": "OK",
            "unit": "RPM",
            "unrec_high": None,
            "unrec_low": None,
            "value": 6700.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Physical_Security_Chassis_Intru": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "General Chassis Intrusion",
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Power_Supply_PS1_Status": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "Presence detected",
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Power_Supply_PS2_Status": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "Presence detected",
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Temperature_CPU_Temp": {
            "crit_high": 100.0,
            "crit_low": 0.0,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 36.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Temperature_DIMMA1_Temp": {
            "crit_high": 85.0,
            "crit_low": 2.0,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 22.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Temperature_DIMMA2_Temp": {
            "crit_high": 85.0,
            "crit_low": 2.0,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 24.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Temperature_Peripheral_Temp": {
            "crit_high": 85.0,
            "crit_low": -7.0,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 27.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Temperature_System_Temp": {
            "crit_high": 85.0,
            "crit_low": -7.0,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 18.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Voltage_12V": {
            "crit_high": 13.22,
            "crit_low": 10.52,
            "status_txt": "OK",
            "unit": "V",
            "unrec_high": None,
            "unrec_low": None,
            "value": 11.95,
            "warn_high": None,
            "warn_low": None,
        },
        "Voltage_AVCC": {
            "crit_high": 3.6,
            "crit_low": 2.49,
            "status_txt": "OK",
            "unit": "V",
            "unrec_high": None,
            "unrec_low": None,
            "value": 3.37,
            "warn_high": None,
            "warn_low": None,
        },
        "Voltage_VDIMM": {
            "crit_high": 1.72,
            "crit_low": 1.12,
            "status_txt": "OK",
            "unit": "V",
            "unrec_high": None,
            "unrec_low": None,
            "value": 1.46,
            "warn_high": None,
            "warn_low": None,
        },
        "Voltage_VSB": {
            "crit_high": 3.6,
            "crit_low": 2.49,
            "status_txt": "OK",
            "unit": "V",
            "unrec_high": None,
            "unrec_low": None,
            "value": 3.3,
            "warn_high": None,
            "warn_low": None,
        },
        "Voltage_Vcpu": {
            "crit_high": 2.09,
            "crit_low": 1.26,
            "status_txt": "OK",
            "unit": "V",
            "unrec_high": None,
            "unrec_low": None,
            "value": 1.78,
            "warn_high": None,
            "warn_low": None,
        },
    },
    {
        "01-Inlet_Ambient": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 24.0,
            "warn_high": None,
            "warn_low": None,
        },
        "CPU_Utilization": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "",
            "unrec_high": None,
            "unrec_low": None,
            "value": 68.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Fan_FAN1_F_Speed": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "RPM",
            "unrec_high": None,
            "unrec_low": None,
            "value": 7200.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Intrusion": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "",
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "M2_Temp0(PCIe1)_(Temperature)": {
            "crit_high": 79.0,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 41.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Megacell_Status": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "",
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Memory_Status": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "error",
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "OEM_Reserved_CPU_Temp": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": None,
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Power_Meter": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "W",
            "unrec_high": None,
            "unrec_low": None,
            "value": 260.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Power_Supply_PS_Status": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "Presence detected",
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Power_Unit_PSU": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "Redundancy Lost",
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "SysHealth_Stat": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "",
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Temperature_Ambient": {
            "crit_high": 42.0,
            "crit_low": 1.0,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 20.0,
            "warn_high": None,
            "warn_low": None,
        },
        "Temperature_DIMM-2A": {
            "crit_high": 115.0,
            "crit_low": None,
            "status_txt": None,
            "unit": None,
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
        "Temperature_Inlet_Temp": {
            "crit_high": 48.0,
            "crit_low": None,
            "status_txt": "OK",
            "unit": "C",
            "unrec_high": None,
            "unrec_low": None,
            "value": 21.0,
            "warn_high": None,
            "warn_low": None,
        },
        "UID": {
            "crit_high": None,
            "crit_low": None,
            "status_txt": "no state reported",
            "unit": "",
            "unrec_high": None,
            "unrec_low": None,
            "value": None,
            "warn_high": None,
            "warn_low": None,
        },
    },
]


@pytest.mark.parametrize(
    [
        "string_table",
        "expected_result",
    ],
    list(zip(_STRING_TABLES, _SECTIONS)),
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_parse_ipmi_sensors(
    string_table: StringTable,
    expected_result,
) -> None:
    assert register.get_section_plugin(SectionName("ipmi_sensors")).parse_function(
        string_table) == expected_result  # type: ignore[arg-type]


@pytest.mark.parametrize(
    [
        "section",
        "params",
        "expected_result",
    ],
    [
        pytest.param(
            _SECTIONS[0],
            [],
            [],
        ),
        pytest.param(
            _SECTIONS[1],
            [],
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
            [{
                "discovery_mode": (
                    "single",
                    {
                        "ignored_sensors": ["UID", "Temperature_Inlet_Temp"],
                        "ignored_sensorstates": ["Redundancy Lost"],
                    },
                )
            }],
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
            [{
                "discovery_mode": (
                    "summarize",
                    {},
                )
            }],
            [
                Service(item="Summary FreeIPMI"),
            ],
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_ipmi_sensors(
    mocker: MockerFixture,
    section,
    params,
    expected_result: DiscoveryResult,
) -> None:
    assert (plugin := register.get_check_plugin(CheckPluginName("ipmi_sensors")))

    mocker.patch(
        "cmk.base.check_legacy_includes.ipmi_sensors.host_name",
        lambda: "whatever",
    )

    with MockHostExtraConf(
            Check("ipmi_sensors"),
            params,
    ):
        assert list(plugin.discovery_function(section)) == expected_result


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
                Result(state=State.UNKNOWN, summary="Status: Presence detected"),
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
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_ipmi_sensors(
    item: str,
    params: Mapping[str, Any],
    section,
    expected_result: CheckResult,
) -> None:
    assert (plugin := register.get_check_plugin(CheckPluginName("ipmi_sensors")))
    assert list(plugin.check_function(
        item=item,
        params=params,
        section=section,
    )) == expected_result
