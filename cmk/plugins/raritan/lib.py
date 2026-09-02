#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import ElPhase, ReadingWithState
from cmk.plugins.lib.temperature import check_temperature, TempParamType

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

# SensorStateEnumeration (EMD-, PDU2, LHX-MIB)
STATE_MAPPING = {
    "-1": (State.CRIT, "unavailable"),
    "0": (State.WARN, "open"),
    "1": (State.OK, "closed"),
    "2": (State.CRIT, "below lower critical"),
    "3": (State.WARN, "below lower warning"),
    "4": (State.OK, "normal"),
    "5": (State.WARN, "above upper warning"),
    "6": (State.CRIT, "above upper critical"),
    "7": (State.OK, "on"),
    "8": (State.CRIT, "off"),
    "9": (State.OK, "detected"),
    "10": (State.CRIT, "not detected"),
    "11": (State.CRIT, "alarmed"),
}

# SensorStateEnumeration (EMD-, PDU2, LHX-MIB) - simplified for plugs (on/off)
PLUG_STATE_MAPPING = {
    "7": "on",
    "8": "off",
}


def elphase_from_readings(readings: Mapping[str, ReadingWithState]) -> ElPhase:
    """Build an ElPhase from readings keyed by the names used in TYPE_MAPPING.

    Readings the electrical phase check does not know about are dropped.
    """
    return ElPhase(
        voltage=readings.get("voltage"),
        current=readings.get("current"),
        output_load=readings.get("output_load"),
        power=readings.get("power"),
        appower=readings.get("appower"),
        energy=readings.get("energy"),
        frequency=readings.get("frequency"),
        differential_current_ac=readings.get("differential_current_ac"),
        differential_current_dc=readings.get("differential_current_dc"),
    )


@dataclass(frozen=True, kw_only=True)
class RaritanSensor:
    availability: str
    state: tuple[State, str]
    sensor_type: str
    sensor_data: Sequence[float]
    sensor_unit: str


type SensorSection = Mapping[str, RaritanSensor]

# The string table must be of the form:
# "X.Y.Z",  # IsAvailable -> True/False (1/0)
# "X.Y.Z",  # Number
# "X.Y.Z",  # Name
# "X.Y.Z",  # Type
# "X.Y.Z",  # State
# "X.Y.Z",  # Units
# "X.Y.Z",  # DecimalDigits -> for scaling the values
# "X.Y.Z",  # Value
# "X.Y.Z",  # LowerCriticalThreshold
# "X.Y.Z",  # LowerWarningThreshold
# "X.Y.Z",  # UpperCriticalThreshold
# "X.Y.Z",  # UpperWarningThreshold


def parse_raritan_sensors(string_table: StringTable) -> SensorSection:
    parsed = {}
    for (
        availability,
        sensor_id,
        sensor_name,
        sensor_type,
        sensor_state,
        sensor_unit,
        sensor_exponent,
        sensor_value_str,
        sensor_lower_crit_str,
        sensor_lower_warn_str,
        sensor_upper_crit_str,
        sensor_upper_warn_str,
    ) in string_table:
        sensor_type, sensor_type_readable = TYPE_MAPPING.get(sensor_type, ("", "Other"))

        extra_name = ""
        if sensor_type_readable != "":
            extra_name += " " + sensor_type_readable

        sensor_name = (f"Sensor {sensor_id}{extra_name} {sensor_name}").strip()

        sensor_unit = UNIT_MAPPING.get(sensor_unit, " Other")

        # binary sensors don't have any values or levels
        if sensor_type in ["binary", ""]:
            sensor_data = []
        else:
            # 1 m/s = 8.11 l/s
            if sensor_unit == " m/s":
                sensor_unit = " l/s"
                factor = 8.11
            else:
                factor = 1
            # if the value is 5 and unitSensorDecimalDigits is 2
            # then actual value is 0.05
            sensor_data = [
                factor * float(x) / pow(10, int(sensor_exponent))
                for x in [
                    sensor_value_str,
                    sensor_lower_crit_str,
                    sensor_lower_warn_str,
                    sensor_upper_crit_str,
                    sensor_upper_warn_str,
                ]
            ]

        parsed[sensor_name] = RaritanSensor(
            availability=availability,
            state=STATE_MAPPING.get(sensor_state, (State.UNKNOWN, "unhandled state")),
            sensor_type=sensor_type,
            sensor_data=sensor_data,
            sensor_unit=sensor_unit,
        )

    return parsed


def discover_raritan_sensors(section: SensorSection, sensor_type: str) -> DiscoveryResult:
    for key, sensor in section.items():
        if sensor.availability == "1" and sensor.sensor_type == sensor_type:
            yield Service(item=key)


def check_raritan_sensors(item: str, section: SensorSection) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    state, state_readable = sensor.state
    unit = sensor.sensor_unit
    reading, _crit_lower, warn_lower, crit, warn = sensor.sensor_data
    infotext = f"{reading}{unit}, status: {state_readable}"

    if state is not State.OK and reading >= warn:
        infotext += f" (device warn/crit at {warn:.1f}{unit}/{crit:.1f}{unit})"
    elif state is not State.OK and reading < warn_lower:
        infotext += f" (device warn/crit below {warn_lower:.1f}{unit}/{warn_lower:.1f}{unit})"

    yield Result(state=state, summary=infotext)
    yield Metric(sensor.sensor_type, reading, levels=(warn, crit))


def check_raritan_sensors_binary(item: str, section: SensorSection) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    state, state_readable = sensor.state
    yield Result(state=state, summary=f"Status: {state_readable}")


def check_raritan_sensors_temp(
    item: str, params: TempParamType, section: SensorSection
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    state, state_readable = sensor.state
    reading, crit_lower, warn_lower, crit, warn = sensor.sensor_data
    yield from check_temperature(
        reading,
        params,
        unique_name=f"raritan_sensors_{item}",
        value_store=get_value_store(),
        dev_unit=sensor.sensor_unit,
        dev_levels=(warn, crit),
        dev_levels_lower=(warn_lower, crit_lower),
        dev_status=int(state),
        dev_status_name=state_readable,
    )


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
