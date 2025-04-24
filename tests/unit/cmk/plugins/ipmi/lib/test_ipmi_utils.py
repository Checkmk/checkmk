#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.ipmi.lib import ipmi


@pytest.mark.parametrize(
    "item, params, sensor, temperature_metrics_only, status_txt_mapping, exp_result",
    [
        (
            "something",
            {},
            ipmi.Sensor(
                status_txt="ok",
                unit="",
                value=None,
                crit_low=None,
                warn_low=None,
                warn_high=None,
                crit_high=None,
            ),
            False,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
            ],
        ),
        (
            "PCH_1.05V",
            {},
            ipmi.Sensor(
                status_txt="ok",
                unit="Volts",
                value=1.04,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            False,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1.04 Volts"),
                Metric("PCH_1.05V", 1.04, levels=(1.13, 1.13)),
            ],
        ),
        (
            "PCH_1.05V",
            {},
            ipmi.Sensor(
                status_txt="ok",
                unit="Volts",
                value=1.04,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            False,
            lambda txt: State.CRIT,
            [
                Result(
                    state=State.CRIT,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1.04 Volts"),
                Metric("PCH_1.05V", 1.04, levels=(1.13, 1.13)),
            ],
        ),
        (
            "PCH_1.05V",
            {},
            ipmi.Sensor(
                status_txt="ok",
                unit="Volts",
                value=1.04,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            True,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1.04 Volts"),
            ],
        ),
        (
            "Temperature",
            {},
            ipmi.Sensor(
                status_txt="ok",
                unit="C",
                value=1.04,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            True,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1.04 C"),
                Metric("value", 1.04, levels=(1.13, 1.13)),
            ],
        ),
        (
            "PCH_1.05V",
            {},
            ipmi.Sensor(
                status_txt="nc",
                unit="Volts",
                value=1.04,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            False,
            lambda txt: State.WARN if txt.startswith("nc") else State.OK,
            [
                Result(
                    state=State.WARN,
                    summary="Status: nc",
                    details="Status: nc (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1.04 Volts"),
                Metric("PCH_1.05V", 1.04, levels=(1.13, 1.13)),
            ],
        ),
        (
            "PCH_1.05V",
            {},
            ipmi.Sensor(
                status_txt="ok",
                unit="Volts",
                value=2.1,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            False,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.CRIT,
                    summary="2.10 Volts (warn/crit at 1.13 Volts/1.13 Volts)",
                    details="2.10 Volts (warn/crit at 1.13 Volts/1.13 Volts)",
                ),
                Metric("PCH_1.05V", 2.1, levels=(1.13, 1.13)),
            ],
        ),
        (
            "PCH_1.05V",
            {},
            ipmi.Sensor(
                status_txt="ok",
                unit="Volts",
                value=0.5,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            False,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.CRIT,
                    summary="0.50 Volts (warn/crit below 0.97 Volts/0.97 Volts)",
                    details="0.50 Volts (warn/crit below 0.97 Volts/0.97 Volts)",
                ),
                Metric("PCH_1.05V", 0.5, levels=(1.13, 1.13)),
            ],
        ),
        (
            "PCH_1.05V",
            {
                "numerical_sensor_levels": [
                    {
                        "sensor_name": "PCH_1.05V",
                        "lower": ("fixed", (1.0, 2.0)),
                        "upper": ("fixed", (1.0, 4.0)),
                    },
                ]
            },
            ipmi.Sensor(
                status_txt="ok",
                unit="Volts",
                value=1.04,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            False,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1.04 Volts"),
                Metric("PCH_1.05V", 1.04, levels=(1.13, 1.13)),
                Result(
                    state=State.CRIT,
                    summary="PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts) (warn/crit below 1.00 Volts/2.00 Volts)",
                    details="PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts) (warn/crit below 1.00 Volts/2.00 Volts)",
                ),
            ],
        ),
        (
            "PCH_1.05V",
            {
                "numerical_sensor_levels": [
                    {
                        "sensor_name": "PCH_1.05V",
                        "upper": ("fixed", (1.0, 4.0)),
                        "lower": ("no_levels", None),
                    },
                ]
            },
            ipmi.Sensor(
                status_txt="ok",
                unit="Volts",
                value=1.04,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            False,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1.04 Volts"),
                Metric("PCH_1.05V", 1.04, levels=(1.13, 1.13)),
                Result(
                    state=State.WARN,
                    summary="PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts)",
                    details="PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts)",
                ),
            ],
        ),
        (
            "PCH_1.05V",
            {"sensor_states": [{"ipmi_state": "ok", "target_state": 3}]},
            ipmi.Sensor(
                status_txt="ok",
                unit="Volts",
                value=1.04,
                crit_low=0.97,
                warn_low=None,
                warn_high=None,
                crit_high=1.13,
            ),
            False,
            lambda txt: State.OK,
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Status: ok",
                    details="Status: ok (service state set by user-configured rules)",
                ),
                Result(state=State.OK, summary="1.04 Volts"),
                Metric("PCH_1.05V", 1.04, levels=(1.13, 1.13)),
            ],
        ),
        (
            "01-Inlet_Ambient",
            {},
            ipmi.Sensor(
                status_txt="OK",
                unit="C",
                value=24.0,
                crit_low=None,
                warn_low=None,
                warn_high=None,
                crit_high=None,
                type_="Temperature",
            ),
            True,
            lambda txt: State.OK,
            [
                Result(
                    state=State.OK,
                    summary="Status: OK",
                    details="Status: OK (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="24.00 C"),
                Metric(name="value", value=24.0),
            ],
        ),
    ],
)
def test_check_ipmi_detailed(
    item: str,
    params: Mapping[str, Any],
    sensor: ipmi.Sensor,
    temperature_metrics_only: bool,
    status_txt_mapping: ipmi.StatusTxtMapping,
    exp_result: CheckResult,
) -> None:
    assert (
        list(
            ipmi.check_ipmi(
                item,
                params,
                {item: sensor},
                temperature_metrics_only,
                status_txt_mapping,
            )
        )
        == exp_result
    )


SECTION = {
    "Ambient": ipmi.Sensor(
        status_txt="ok",
        unit="degrees_C",
        value=18.5,
        crit_low=1.0,
        warn_low=6.0,
        warn_high=37.0,
        crit_high=42.0,
    ),
    "CPU": ipmi.Sensor(
        status_txt="ok",
        unit="degrees_C",
        value=33.0,
        crit_low=None,
        warn_low=None,
        warn_high=95.0,
        crit_high=99.0,
    ),
    "I2C4_error_ratio": ipmi.Sensor(
        status_txt="ok",
        unit="percent",
        value=0.0,
        crit_low=None,
        warn_low=None,
        warn_high=10.0,
        crit_high=20.0,
    ),
    "PCH_1.05V": ipmi.Sensor(
        status_txt="ok",
        unit="Volts",
        value=1.04,
        crit_low=0.97,
        warn_low=None,
        warn_high=None,
        crit_high=1.13,
    ),
    "Total_Power": ipmi.Sensor(
        status_txt="ok",
        unit="Watts",
        value=48.0,
        crit_low=None,
        warn_low=None,
        warn_high=None,
        crit_high=498.0,
    ),
    "CMOS_Battery": ipmi.Sensor(
        status_txt="ok",
        unit="",
        value=None,
        crit_low=None,
        warn_low=None,
        warn_high=None,
        crit_high=None,
    ),
    "MSR_Info_Log": ipmi.Sensor(
        status_txt="ns (No Reading)",
        unit="",
        value=None,
        crit_low=None,
        warn_low=None,
        warn_high=None,
        crit_high=None,
    ),
    "PS1_Status": ipmi.Sensor(
        status_txt="ok (Presence detected, Failure detected)",
        unit="",
        value=None,
        crit_low=None,
        warn_low=None,
        warn_high=None,
        crit_high=None,
    ),
    "Power_Redundancy": ipmi.Sensor(
        status_txt="ok (Fully Redundant)",
        unit="",
        value=None,
        crit_low=None,
        warn_low=None,
        warn_high=None,
        crit_high=None,
    ),
    "VCORE": ipmi.Sensor(
        status_txt="ok (State Deasserted)",
        unit="",
        value=None,
        crit_low=None,
        warn_low=None,
        warn_high=None,
        crit_high=None,
    ),
}


@pytest.mark.parametrize(
    "params, status_txt_mapping, exp_result",
    [
        (
            {},
            lambda txt: State.OK,
            [
                Metric("ambient_temp", 18.5),
                Result(state=State.OK, summary="10 sensors in total"),
                Result(state=State.OK, summary="10 sensors ok"),
                Result(
                    state=State.OK,
                    notice="Ambient: ok",
                    details="Ambient: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU: ok",
                    details="CPU: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C4_error_ratio: ok",
                    details="I2C4_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PCH_1.05V: ok",
                    details="PCH_1.05V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Total_Power: ok",
                    details="Total_Power: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CMOS_Battery: ok",
                    details="CMOS_Battery: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MSR_Info_Log: ns (No Reading)",
                    details="MSR_Info_Log: ns (No Reading) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS1_Status: ok (Presence detected, Failure detected)",
                    details="PS1_Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Redundancy: ok (Fully Redundant)",
                    details="Power_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VCORE: ok (State Deasserted)",
                    details="VCORE: ok (State Deasserted) (service state derived from sensor events)",
                ),
            ],
        ),
        (
            {},
            lambda txt: ("Failure detected" in txt and State.CRIT)
            or ("State Deasserted" in txt and State.WARN or State.OK),
            [
                Metric("ambient_temp", 18.5),
                Result(state=State.OK, summary="10 sensors in total"),
                Result(state=State.OK, summary="8 sensors ok"),
                Result(
                    state=State.OK,
                    notice="Ambient: ok",
                    details="Ambient: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU: ok",
                    details="CPU: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C4_error_ratio: ok",
                    details="I2C4_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PCH_1.05V: ok",
                    details="PCH_1.05V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Total_Power: ok",
                    details="Total_Power: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CMOS_Battery: ok",
                    details="CMOS_Battery: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MSR_Info_Log: ns (No Reading)",
                    details="MSR_Info_Log: ns (No Reading) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Redundancy: ok (Fully Redundant)",
                    details="Power_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(state=State.WARN, summary="1 sensors warning"),
                Result(
                    state=State.WARN,
                    notice="VCORE: ok (State Deasserted)",
                    details="VCORE: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(state=State.CRIT, summary="1 sensors critical"),
                Result(
                    state=State.CRIT,
                    notice="PS1_Status: ok (Presence detected, Failure detected)",
                    details="PS1_Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
                ),
            ],
        ),
        (
            {"ignored_sensors": ["CPU", "VCORE"]},
            lambda txt: State.OK,
            [
                Metric("ambient_temp", 18.5),
                Result(state=State.OK, summary="10 sensors in total"),
                Result(state=State.OK, summary="8 sensors ok"),
                Result(
                    state=State.OK,
                    notice="Ambient: ok",
                    details="Ambient: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C4_error_ratio: ok",
                    details="I2C4_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PCH_1.05V: ok",
                    details="PCH_1.05V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Total_Power: ok",
                    details="Total_Power: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CMOS_Battery: ok",
                    details="CMOS_Battery: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MSR_Info_Log: ns (No Reading)",
                    details="MSR_Info_Log: ns (No Reading) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS1_Status: ok (Presence detected, Failure detected)",
                    details="PS1_Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Redundancy: ok (Fully Redundant)",
                    details="Power_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="2 sensors skipped"),
                Result(state=State.OK, notice="CPU: ok"),
                Result(state=State.OK, notice="VCORE: ok (State Deasserted)"),
            ],
        ),
        (
            {"ignored_sensorstates": ["ns", "nr", "na"]},
            lambda txt: State.OK,
            [
                Metric("ambient_temp", 18.5),
                Result(state=State.OK, summary="10 sensors in total"),
                Result(state=State.OK, summary="9 sensors ok"),
                Result(
                    state=State.OK,
                    notice="Ambient: ok",
                    details="Ambient: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU: ok",
                    details="CPU: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C4_error_ratio: ok",
                    details="I2C4_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PCH_1.05V: ok",
                    details="PCH_1.05V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Total_Power: ok",
                    details="Total_Power: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CMOS_Battery: ok",
                    details="CMOS_Battery: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS1_Status: ok (Presence detected, Failure detected)",
                    details="PS1_Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Redundancy: ok (Fully Redundant)",
                    details="Power_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VCORE: ok (State Deasserted)",
                    details="VCORE: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1 sensors skipped"),
                Result(state=State.OK, notice="MSR_Info_Log: ns (No Reading)"),
            ],
        ),
        (
            {
                "ignored_sensorstates": ["ns", "nr", "na"],
                "sensor_states": [{"ipmi_state": "ok", "target_state": 1}],
            },
            lambda txt: State.OK,
            [
                Metric("ambient_temp", 18.5),
                Result(
                    state=State.OK,
                    summary="10 sensors in total",
                ),
                Result(state=State.WARN, summary="9 sensors warning"),
                Result(
                    state=State.WARN,
                    notice="Ambient: ok",
                    details="Ambient: ok (service state set by user-configured rules)",
                ),
                Result(
                    state=State.WARN,
                    notice="CPU: ok",
                    details="CPU: ok (service state set by user-configured rules)",
                ),
                Result(
                    state=State.WARN,
                    notice="I2C4_error_ratio: ok",
                    details="I2C4_error_ratio: ok (service state set by user-configured rules)",
                ),
                Result(
                    state=State.WARN,
                    notice="PCH_1.05V: ok",
                    details="PCH_1.05V: ok (service state set by user-configured rules)",
                ),
                Result(
                    state=State.WARN,
                    notice="Total_Power: ok",
                    details="Total_Power: ok (service state set by user-configured rules)",
                ),
                Result(
                    state=State.WARN,
                    notice="CMOS_Battery: ok",
                    details="CMOS_Battery: ok (service state set by user-configured rules)",
                ),
                Result(
                    state=State.WARN,
                    notice="PS1_Status: ok (Presence detected, Failure detected)",
                    details="PS1_Status: ok (Presence detected, Failure detected) (service state set by user-configured rules)",
                ),
                Result(
                    state=State.WARN,
                    notice="Power_Redundancy: ok (Fully Redundant)",
                    details="Power_Redundancy: ok (Fully Redundant) (service state set by user-configured rules)",
                ),
                Result(
                    state=State.WARN,
                    notice="VCORE: ok (State Deasserted)",
                    details="VCORE: ok (State Deasserted) (service state set by user-configured rules)",
                ),
                Result(state=State.OK, summary="1 sensors skipped"),
                Result(state=State.OK, notice="MSR_Info_Log: ns (No Reading)"),
            ],
        ),
        (
            {
                "numerical_sensor_levels": [
                    {
                        "sensor_name": "PCH_1.05V",
                        "upper": ("fixed", (1.0, 4.0)),
                        "lower": ("no_levels", None),
                    },
                ]
            },
            lambda txt: State.OK,
            [
                Metric("ambient_temp", 18.5),
                Result(state=State.OK, summary="10 sensors in total"),
                Result(state=State.OK, summary="9 sensors ok"),
                Result(
                    state=State.OK,
                    notice="Ambient: ok",
                    details="Ambient: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU: ok",
                    details="CPU: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C4_error_ratio: ok",
                    details="I2C4_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Total_Power: ok",
                    details="Total_Power: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CMOS_Battery: ok",
                    details="CMOS_Battery: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MSR_Info_Log: ns (No Reading)",
                    details="MSR_Info_Log: ns (No Reading) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS1_Status: ok (Presence detected, Failure detected)",
                    details="PS1_Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Redundancy: ok (Fully Redundant)",
                    details="Power_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VCORE: ok (State Deasserted)",
                    details="VCORE: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(state=State.WARN, summary="1 sensors warning"),
                Result(
                    state=State.WARN,
                    summary="PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts)",
                    details="PCH_1.05V: ok (service state derived from sensor events), PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts)",
                ),
            ],
        ),
    ],
)
def test_check_ipmi_summarized(
    params: Mapping[str, object], status_txt_mapping: ipmi.StatusTxtMapping, exp_result: CheckResult
) -> None:
    assert (
        list(
            ipmi.check_ipmi(
                "Summary",
                params,
                SECTION,
                False,
                status_txt_mapping,
            )
        )
        == exp_result
    )


def test_freeipmi_supplied_state_wins() -> None:
    assert list(
        ipmi.check_ipmi(
            "Summary",
            {},
            {
                "PS1_Status": ipmi.Sensor(
                    status_txt="ok (Presence detected, Failure detected)",
                    unit="",
                    state=State.WARN,
                    value=None,
                    crit_low=None,
                    warn_low=None,
                    warn_high=None,
                    crit_high=None,
                )
            },
            False,
            lambda x: State.CRIT,
        )
    ) == [
        Result(state=State.OK, summary="1 sensors in total"),
        Result(state=State.WARN, summary="1 sensors warning"),
        Result(
            state=State.WARN,
            notice="PS1_Status: ok (Presence detected, Failure detected)",
            details="PS1_Status: ok (Presence detected, Failure detected) (service state reported by freeipmi)",
        ),
    ]
