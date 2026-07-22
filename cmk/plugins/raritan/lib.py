#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import equals

DETECT_RARITAN = equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.6")

TYPE_MAPPING = {
    "1": ("current", "RMS"),
    "2": ("peak", "Peak"),
    "3": ("unbalanced", "Unbalanced"),
    "4": ("voltage", "RMS"),
    "5": ("power", "Active"),
    "6": ("appower", "Apparent"),
    # power factor is defined as the ratio of the real power flowing
    # to the load to the apparent power
    "7": ("power_factor", "Power Factor"),
    "8": ("energy", "Active"),
    "9": ("energy", "Apparent"),
    "10": ("temp", ""),
    "11": ("humidity", ""),
    "12": ("airflow", ""),
    "13": ("pressure_pa", "Air"),
    "14": ("binary", "On/Off"),
    "15": ("binary", "Trip"),
    "16": ("binary", "Vibration"),
    "17": ("binary", "Water Detector"),
    "18": ("binary", "Smoke Detector"),
    "19": ("binary", ""),
    "20": ("binary", "Contact"),
    "21": ("fanspeed", ""),
    "26": ("residual_current", "Residual Current"),
    "30": ("", "Other"),
    "31": ("", "None"),
}

UNIT_MAPPING = {
    "-1": "",
    "0": " Other",
    "1": " V",
    "2": " A",
    "3": " W",
    "4": " VA",
    "5": " Wh",
    "6": " VAh",
    # for dev_unit in check_temperature
    "7": "c",
    "8": " hz",
    "9": "%",
    "10": " m/s",
    "11": " Pa",
    # 1 psi = 6894,757293168 Pa
    "12": " psi",
    "13": " g",
    # for dev_unit in check_temperature
    "14": "f",
    "15": " ft",
    "16": " inch",
    "17": " cm",
    "18": " m",
    "19": " RPM",
}


class SnmpBitsModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    BIT_MAPPING: ClassVar[dict[int, str]]

    @classmethod
    def from_snmp_bits(
        cls,
        value: str | bytes | bytearray | Sequence[int],
    ) -> Self:
        raw = value.encode("latin-1") if isinstance(value, str) else value
        return cls.model_validate(
            {name: cls._bit_is_set(raw, bit_number) for bit_number, name in cls.BIT_MAPPING.items()}
        )

    @staticmethod
    def _bit_is_set(
        value: bytes | bytearray | Sequence[int],
        bit_number: int,
    ) -> bool:
        byte_index, bit_index = divmod(bit_number, 8)

        if byte_index >= len(value):
            return False

        return bool(value[byte_index] & (0x80 >> bit_index))


class InletDeviceCapabilities(SnmpBitsModel):
    BIT_MAPPING = {
        0: "rmsCurrent",
        1: "peakCurrent",
        2: "unbalancedCurrent",
        3: "rmsVoltage",
        4: "activePower",
        5: "apparentPower",
        6: "powerFactor",
        7: "activeEnergy",
        8: "apparentEnergy",
        21: "surgeProtectorStatus",
        22: "frequency",
        23: "phaseAngle",
        25: "residualCurrent",
        26: "rcmState",
        28: "reactivePower",
        31: "powerQuality",
        34: "displacementPowerFactor",
        35: "residualDcCurrent",
    }

    rmsCurrent: bool = False
    peakCurrent: bool = False
    unbalancedCurrent: bool = False
    rmsVoltage: bool = False
    activePower: bool = False
    apparentPower: bool = False
    powerFactor: bool = False
    activeEnergy: bool = False
    apparentEnergy: bool = False
    surgeProtectorStatus: bool = False
    frequency: bool = False
    phaseAngle: bool = False
    residualCurrent: bool = False
    rcmState: bool = False
    reactivePower: bool = False
    powerQuality: bool = False
    displacementPowerFactor: bool = False
    residualDcCurrent: bool = False


class InletPoleCapabilities(SnmpBitsModel):
    BIT_MAPPING = {
        0: "rmsCurrent",
        1: "peakCurrent",
        3: "rmsVoltage",
        4: "activePower",
        5: "apparentPower",
        6: "powerFactor",
        7: "activeEnergy",
        8: "apparentEnergy",
        23: "phaseAngle",
        24: "rmsVoltageLN",
        25: "residualCurrent",
        26: "rcmState",
        28: "reactivePower",
        34: "displacementPowerFactor",
        35: "residualDcCurrent",
    }

    rmsCurrent: bool = False
    peakCurrent: bool = False
    rmsVoltage: bool = False
    activePower: bool = False
    apparentPower: bool = False
    powerFactor: bool = False
    activeEnergy: bool = False
    apparentEnergy: bool = False
    phaseAngle: bool = False
    rmsVoltageLN: bool = False
    residualCurrent: bool = False
    rcmState: bool = False
    reactivePower: bool = False
    displacementPowerFactor: bool = False
    residualDcCurrent: bool = False


class InletSensorEnabledThresholds(SnmpBitsModel):
    BIT_MAPPING = {
        0: "lowerCritical",
        1: "lowerWarning",
        2: "upperWarning",
        3: "upperCritical",
    }

    lowerCritical: bool = False
    lowerWarning: bool = False
    upperWarning: bool = False
    upperCritical: bool = False


class PDU(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    pdu_index: str
    label: str
    name: str
    plug: str
    pole_count: str
    rated_voltage: str
    rated_current: str
    rated_frequency: str
    rated_va: str
    plug_descriptor: str
    enable_state: str
    device_capabilities: InletDeviceCapabilities
    pole_capabilities: InletPoleCapabilities


class SensorValues(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    sensor_value: float
    sensor_upper_crit: float
    sensor_upper_warn: float


class Sensor(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    availability: str
    sensor_name: str
    sensor_type: str
    sensor_values: SensorValues
    sensor_unit: str
    sensor_thresholds: InletSensorEnabledThresholds


class RaritanData(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    pdu: PDU
    sensors: dict[str, dict[str, Sensor]] = Field(default_factory=dict)
