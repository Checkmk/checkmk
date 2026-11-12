#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Annotated, ClassVar, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringByteTable,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingState, ReadingWithState
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


def elphase_from_readings(
        readings: Mapping[str, ReadingWithState]
) -> ElPhase:
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


class ParsedModel(BaseModel):
    """Immutable parsed records; reject programming mistakes instead of coercing them."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


@dataclass(frozen=True)
class SensorIndex:
    """PDU2-MIB sensor identity; inlet and outlet tables remain separate."""

    pdu: str
    connector: str
    pole: str | None
    sensor_type: str

    @classmethod
    def from_oid(cls, oid_end: str) -> Self:
        match oid_end.split("."):
            case [pdu, connector, sensor_type]:
                return cls(pdu, connector, None, sensor_type)
            case [pdu, connector, pole, sensor_type]:
                return cls(pdu, connector, pole, sensor_type)
            case _:
                raise ValueError(f"Invalid PDU2-MIB sensor index: {oid_end!r}")


def connector_service_labels(
        configuration: StringTable,
        indices: Sequence[SensorIndex],
        *,
        connector_kind: str = "Inlet"
) -> dict[tuple[str, str], str]:
    """Use inletLabel/outletLabel without losing missing or repeated identities."""
    labels = {(pdu, inlet): label.strip()
              for oid_end, label in configuration
              for pdu, inlet in [oid_end.split(".")]}
    identities = set(labels) | {(index.pdu, index.connector) for index in indices}
    pdus = {pdu for pdu, _inlet in identities}
    names = {}
    for identity in sorted(identities):
        pdu, inlet = identity
        label = labels.get(identity) or f"{connector_kind} {inlet}"
        names[identity] = label if len(pdus) == 1 else f"PDU {pdu} {label}"
    # A label is display text, not an identity. Never overwrite another inlet
    # even when a real label happens to match a generated fallback name.
    while len(set(names.values())) != len(names):
        counts = Counter(names.values())
        names = {
            identity: name if counts[name] == 1 else (
                f"{name} [{connector_kind} {identity[0]}.{identity[1]}]"
                if len(pdus) > 1 else f"{name} [{connector_kind} {identity[1]}]"
            )
            for identity, name in names.items()
        }
    return names


def pole_line_labels(
    configuration: StringTable, indices: Sequence[SensorIndex]
) -> dict[tuple[str, str, str], str]:
    """Resolve inletPoleLine/outletPoleLine independently of the numeric pole index."""
    line_mapping = {"1": "L1", "2": "L2", "3": "L3", "4": "N", "5": "DC+", "6": "DC-"}
    names = {
        (pdu, inlet, pole): line_mapping.get(line, f"Pole {pole}")
        for oid_end, line in configuration
        for pdu, inlet, pole in [oid_end.split(".")]
    }
    for index in indices:
        if index.pole is not None:
            names.setdefault((index.pdu, index.connector, index.pole), f"Pole {index.pole}")
    counts = Counter((pdu, inlet, name) for (pdu, inlet, _pole), name in names.items())
    return {
        (pdu, inlet, pole): name if counts[pdu, inlet, name] == 1 else f"{name} [Pole {pole}]"
        for (pdu, inlet, pole), name in names.items()
    }


# Prefer automatic integer conversion, but retain empty/invalid SNMP text.
# Conversion errors must affect only the check that actually needs that field.
type SnmpInteger = Annotated[int | str, Field(union_mode="left_to_right")]


class PduSensorConfiguration(ParsedModel):
    """Configuration columns in fetch order, shared by all four table levels."""

    model_config = ConfigDict(strict=False)

    oid_end: str
    unit: str = ""
    digits: SnmpInteger = ""
    unsigned_crit: SnmpInteger = ""
    unsigned_warn: SnmpInteger = ""
    enabled_thresholds: tuple[int, ...] = ()
    signed_minimum: SnmpInteger = ""
    signed_crit: SnmpInteger = ""
    signed_warn: SnmpInteger = ""
    unsigned_lower_crit: SnmpInteger = ""
    unsigned_lower_warn: SnmpInteger = ""
    signed_lower_crit: SnmpInteger = ""
    signed_lower_warn: SnmpInteger = ""


class PduSensorMeasurement(ParsedModel):
    """Measurement columns in fetch order; only SNMP availability 1 is true."""

    model_config = ConfigDict(strict=False)

    oid_end: str
    availability: Annotated[bool, BeforeValidator(lambda value: value == "1" if isinstance(value, str) else value)]
    state: str
    unsigned_value: SnmpInteger
    signed_value: SnmpInteger


class PduSensor(ParsedModel):
    index: SensorIndex
    configuration: PduSensorConfiguration | None
    measurement: PduSensorMeasurement | None


class ResidualSensor(ParsedModel):
    index: SensorIndex
    available: bool
    state: str
    value: float | None
    upper: tuple[float | None, float | None]
    lower: tuple[float | None, float | None]


type ElectricalSection = Mapping[str, ElPhase]
type ResidualSection = Mapping[str, Mapping[str, ResidualSensor]]


class PduSection(ParsedModel):
    """One fetched and parsed table level, shared by independent checks.

    Configuration-only and measurement-only rows retain their identities.
    Electrical and residual views preserve their respective discovery policies.
    Conversion failures are retained per view and raised by its accessor, so
    sharing raw data does not couple previously independent check failures.
    """

    sensors: tuple[PduSensor, ...] = ()
    electrical: dict[str, ElPhase] = Field(default_factory=dict)
    residual: dict[str, dict[str, ResidualSensor]] = Field(default_factory=dict)
    electrical_error: str | None = None
    residual_error: str | None = None

    def get_electrical(self) -> ElectricalSection:
        if self.electrical_error is not None:
            raise ValueError(self.electrical_error)
        return self.electrical

    def get_residual(self) -> ResidualSection:
        if self.residual_error is not None:
            raise ValueError(self.residual_error)
        return self.residual


def scale_sensor_value(value: int | str, digits: int | str) -> float:
    """Scale a numeric sensor field and reject values unusable for monitoring."""
    scaled = float(value) / 10 ** int(digits)
    if not isfinite(scaled):
        raise ValueError("Non-finite sensor value")
    return scaled


def parse_electrical_readings(sensors: Sequence[PduSensor]) -> dict[SensorIndex, ElPhase]:
    """Use full indices, native signedness and the existing quantity priorities."""
    mapping = {"1": "current", "4": "voltage", "5": "power", "6": "appower",
               "8": "energy", "25": "voltage"}
    readings: dict[SensorIndex, dict[str, ReadingWithState]] = {}
    for sensor in sensors:
        index, config, measurement = sensor.index, sensor.configuration, sensor.measurement
        if measurement is None or not measurement.availability or index.sensor_type not in mapping:
            continue
        if config is None or config.digits == "":
            continue
        signed = config.signed_minimum != "" and int(config.signed_minimum) < 0
        value_str = measurement.signed_value if signed else measurement.unsigned_value
        if value_str == "":
            continue
        group = SensorIndex(index.pdu, index.connector, index.pole, "")
        key = mapping[index.sensor_type]
        group_readings = readings.setdefault(group, {})
        if index.sensor_type == "25" and "voltage" in group_readings:
            continue
        state, text = STATE_MAPPING.get(measurement.state, (State.UNKNOWN, "unhandled state"))
        group_readings[key] = ReadingWithState(
            value=scale_sensor_value(value_str, config.digits),
            state=None if state is State.OK else ReadingState(state=state, text=text),
        )
    return {index: elphase_from_readings(values) for index, values in readings.items()}


def parse_electrical_section(
    sensors: Sequence[PduSensor], labels_table: StringTable, lines_table: StringTable,
    *, connector_kind: str, poles: bool = False,
) -> dict[str, ElPhase]:
    """Preserve electrical names using measurement identities, not configuration-only rows."""
    indices = [sensor.index for sensor in sensors if sensor.measurement is not None]
    labels = connector_service_labels(labels_table, indices, connector_kind=connector_kind)
    lines = pole_line_labels(lines_table, indices) if poles else {}
    section = {}
    for index, elphase in parse_electrical_readings(sensors).items():
        item = labels[index.pdu, index.connector]
        if poles:
            item += f" Phase {lines[index.pdu, index.connector, index.pole]}"
        section[item] = elphase
    return section


def inlet_item(
    index: SensorIndex, inlets: set[tuple[str, str]], *, summary: str = "Summary"
) -> str:
    """Keep legacy names for the standard single-PDU, single-inlet case."""
    suffix = summary if index.pole is None else f"Phase {index.pole}"
    if inlets == {("1", "1")}:
        return suffix
    prefix = f"Inlet {index.connector}"
    if len({pdu for pdu, _inlet in inlets}) > 1:
        prefix = f"PDU {index.pdu} {prefix}"
    return f"{prefix} {suffix}".strip()


def _parse_residual_sensor_data(sensor_data: Sequence[PduSensor]) -> list[ResidualSensor]:
    sensors = []
    for sensor in sensor_data:
        index = sensor.index
        if index.sensor_type not in {"1", "26", "27", "36", "55"}:
            continue
        config, measurement = sensor.configuration, sensor.measurement
        available = measurement is not None and measurement.availability
        state = measurement.state if measurement else ""
        signed = config is not None and config.signed_minimum != "" and int(config.signed_minimum) < 0
        thresholds = InletSensorEnabledThresholds.from_snmp_bits(config.enabled_thresholds if config else ())

        def scale(raw: int | str) -> float | None:
            return scale_sensor_value(raw, config.digits) if config and raw != "" and config.digits != "" else None

        numeric = available and state != "-1" and config is not None and config.unit == "2" and index.sensor_type != "27"
        sensors.append(ResidualSensor(
            index=index, available=available, state=state,
            value=scale(measurement.signed_value if signed else measurement.unsigned_value) if numeric else None,
            upper=(
                scale(config.signed_warn if signed else config.unsigned_warn) if thresholds.upperWarning else None,
                scale(config.signed_crit if signed else config.unsigned_crit) if thresholds.upperCritical else None,
            ),
            lower=(
                scale(config.signed_lower_warn if signed else config.unsigned_lower_warn) if thresholds.lowerWarning else None,
                scale(config.signed_lower_crit if signed else config.unsigned_lower_crit) if thresholds.lowerCritical else None,
            ),
        ))
    return sensors


def parse_residual_section(
    sensor_data: Sequence[PduSensor], labels_table: StringTable, lines_table: StringTable,
    *, poles: bool = False,
) -> dict[str, dict[str, ResidualSensor]]:
    """Build the residual view without borrowing readings from another table level."""
    inlets = {tuple(row[0].split(".")) for row in labels_table}
    sensors = _parse_residual_sensor_data(sensor_data)
    inlets.update((sensor.index.pdu, sensor.index.connector) for sensor in sensors)
    indices = [sensor.index for sensor in sensors]
    labels = connector_service_labels(labels_table, indices)
    lines = pole_line_labels(lines_table, indices) if poles else {}
    section: dict[str, dict[str, ResidualSensor]] = {}
    for sensor in sensors:
        index = sensor.index
        if poles:
            item = f"{labels[index.pdu, index.connector]} Phase {lines[index.pdu, index.connector, index.pole]}"
        else:
            item = inlet_item(index, inlets, summary="Summary" if inlets == {("1", "1")} else "")
        section.setdefault(item, {})[index.sensor_type] = sensor
    return section


def discover_pdu_electrical(
        section: PduSection
) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.get_electrical())


def check_pdu_electrical(
        item: str,
        params: Mapping[str, object],
        section: PduSection
) -> CheckResult:
    if section.electrical_error is not None:
        yield Result(state=State.UNKNOWN, summary=f"Invalid electrical data: {section.electrical_error}")
        return
    if (elphase := section.get_electrical().get(item)) is not None:
        yield from check_elphase(params, elphase)


type SensorData = tuple[()] | tuple[float, float | None, float | None, float | None, float | None]


class ExternalSensorRow(ParsedModel):
    """Common external sensor columns, normalized by each family's SNMP adapter."""

    availability: str
    sensor_id: str
    sensor_name: str
    sensor_type: str
    sensor_state: str
    sensor_unit: str
    sensor_exponent: str
    sensor_value_str: str
    sensor_lower_crit_str: str
    sensor_lower_warn_str: str
    sensor_upper_crit_str: str
    sensor_upper_warn_str: str
    enabled_thresholds: tuple[int, ...] | None = None


class RaritanSensor(ParsedModel):
    availability: str
    state: tuple[State, str]
    sensor_type: str
    sensor_data: SensorData
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


def parse_raritan_sensors(
        string_table: StringTable | StringByteTable | Sequence[ExternalSensorRow],
        *,
        pdu_indexed: bool = False
) -> SensorSection:
    parsed = {}
    multiple_pdus = pdu_indexed and len({
        (row.sensor_id if isinstance(row, ExternalSensorRow) else str(row[1])).split(".")[0]
        for row in string_table
    }) > 1
    for row in string_table:
        # Only the optional BITS column is binary; all preceding OIDs are strings.
        if isinstance(row, ExternalSensorRow):
            raw = row
        else:
            fields = dict(zip(tuple(ExternalSensorRow.model_fields)[:12], row[:12], strict=True))
            if len(row) > 12:
                bits = row[12]
                fields["enabled_thresholds"] = tuple(bits.encode("latin-1") if isinstance(bits, str) else bits)
            raw = ExternalSensorRow.model_validate(fields)
        availability = raw.availability
        sensor_id = raw.sensor_id
        sensor_name = raw.sensor_name
        sensor_type = raw.sensor_type
        sensor_state = raw.sensor_state
        sensor_unit = raw.sensor_unit
        sensor_exponent = raw.sensor_exponent
        sensor_value_str = raw.sensor_value_str
        sensor_lower_crit_str = raw.sensor_lower_crit_str
        sensor_lower_warn_str = raw.sensor_lower_warn_str
        sensor_upper_crit_str = raw.sensor_upper_crit_str
        sensor_upper_warn_str = raw.sensor_upper_warn_str
        sensor_type, sensor_type_readable = TYPE_MAPPING.get(sensor_type, ("", "Other"))

        extra_name = ""
        if sensor_type_readable != "":
            extra_name += " " + sensor_type_readable

        pdu_prefix = ""
        if pdu_indexed:
            pdu, sensor_id = sensor_id.split(".")
            pdu_prefix = f"{pdu}/" if multiple_pdus else ""
        sensor_name = (f"{pdu_prefix}Sensor {sensor_id}{extra_name} {sensor_name}").strip()

        sensor_unit = UNIT_MAPPING.get(sensor_unit, " Other")

        # binary sensors don't have any values or levels
        state = STATE_MAPPING.get(sensor_state, (State.UNKNOWN, "unhandled state"))
        sensor_data: list[float | None] = []
        if sensor_type in ["binary", ""]:
            # Availability affects discovery; binary checks retain the original
            # reported state even when the availability flag is unset.
            pass
        elif availability != "1":
            state = (State.CRIT, "unavailable")
        else:
            # if the value is 5 and unitSensorDecimalDigits is 2
            # then actual value is 0.05
            try:
                exponent = int(sensor_exponent)
                # Larger exponents cannot be converted to the float used by
                # Checkmk. Bound them before allocating enormous integers.
                if not -308 <= exponent <= 308:
                    raise ValueError("Sensor exponent outside floating-point range")
                scale = 10 ** exponent
                reading = float(sensor_value_str) / scale
                if not isfinite(reading):
                    raise ValueError("Non-finite sensor reading")
                sensor_data.append(reading)
            except (ValueError, OverflowError):
                state = (State.UNKNOWN, "invalid or missing sensor reading")
            else:
                active = (
                    InletSensorEnabledThresholds.from_snmp_bits(raw.enabled_thresholds)
                    if raw.enabled_thresholds is not None else None
                )
                for threshold_raw, enabled in [
                    (sensor_lower_crit_str, active is None or active.lowerCritical),
                    (sensor_lower_warn_str, active is None or active.lowerWarning),
                    (sensor_upper_crit_str, active is None or active.upperCritical),
                    (sensor_upper_warn_str, active is None or active.upperWarning),
                ]:
                    try:
                        threshold = float(threshold_raw) / scale if enabled else None
                        if threshold is not None and not isfinite(threshold):
                            threshold = None
                    except (ValueError, OverflowError):
                        threshold = None
                    sensor_data.append(threshold)

        parsed[sensor_name] = RaritanSensor(
            availability=availability,
            state=state,
            sensor_type=sensor_type,
            sensor_data=tuple(sensor_data),
            sensor_unit=sensor_unit,
        )

    return parsed


def sensor_reading_problem(
        sensor: RaritanSensor
) -> Result | None:
    if sensor.availability != "1":
        return Result(state=State.CRIT, summary="Sensor is unavailable")
    if not sensor.sensor_data:
        return Result(state=State.UNKNOWN, summary="Invalid or missing sensor reading")
    return None


def discover_raritan_sensors(
        section: SensorSection,
        sensor_type: str
) -> DiscoveryResult:
    for key, sensor in section.items():
        if sensor.availability == "1" and sensor.sensor_type == sensor_type:
            yield Service(item=key)


def check_raritan_sensors(
        item: str,
        section: SensorSection
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    state, state_readable = sensor.state
    if (problem := sensor_reading_problem(sensor)) is not None:
        yield problem
        return
    unit = sensor.sensor_unit
    reading, crit_lower, warn_lower, crit, warn = sensor.sensor_data
    assert reading is not None
    infotext = f"{reading}{unit}, status: {state_readable}"

    def level_text(value: float | None) -> str:
        return "disabled" if value is None else f"{value:.1f}{unit}"

    if state is not State.OK and any(
        reading >= limit for limit in (warn, crit) if limit is not None
    ):
        infotext += f" (device warn/crit at {level_text(warn)}/{level_text(crit)})"
    elif state is not State.OK and any(
        reading < limit for limit in (warn_lower, crit_lower) if limit is not None
    ):
        infotext += f" (device warn/crit below {level_text(warn_lower)}/{level_text(crit_lower)})"

    yield Result(state=state, summary=infotext)
    metric_name = (
        "raritan_air_velocity"
        if sensor.sensor_type == "airflow" and unit == " m/s" else sensor.sensor_type
    )
    # Display the device's unit above; pressure performance data is always Pa.
    factor = 6894.757293168 if sensor.sensor_type == "pressure_pa" and unit == " psi" else 1.0
    yield Metric(
        metric_name,
        reading * factor,
        levels=(warn * factor if warn is not None else None, crit * factor if crit is not None else None),
    )


def check_raritan_sensors_binary(
        item: str,
        section: SensorSection
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    state, state_readable = sensor.state
    yield Result(state=state, summary=f"Status: {state_readable}")


def check_raritan_sensors_temp(
        item: str,
        params: TempParamType,
        section: SensorSection
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    state, state_readable = sensor.state
    if (problem := sensor_reading_problem(sensor)) is not None:
        yield problem
        return
    reading, crit_lower, warn_lower, crit, warn = sensor.sensor_data
    assert reading is not None

    def temperature_levels(
        warning: float | None, critical: float | None, *, lower: bool = False
    ) -> tuple[float, float] | None:
        if warning is None and critical is None:
            return None
        # The temperature helper requires numeric pairs, including when only
        # one threshold is enabled. Infinity leaves the other threshold inactive.
        inactive = float("-inf") if lower else float("inf")
        return (
            warning if warning is not None else inactive,
            critical if critical is not None else inactive,
        )

    for result in check_temperature(
        reading,
        params,
        unique_name=f"raritan_sensors_{item}",
        value_store=get_value_store(),
        dev_unit=sensor.sensor_unit,
        dev_levels=temperature_levels(warn, crit),
        dev_levels_lower=temperature_levels(warn_lower, crit_lower, lower=True),
        dev_status=int(state),
        dev_status_name=state_readable,
    ):
        if isinstance(result, Metric):
            # Keep internal inactive thresholds out of performance data.
            warn_level, crit_level = result.levels
            yield Metric(
                result.name, result.value,
                levels=(
                    warn_level if warn_level is not None and isfinite(warn_level) else None,
                    crit_level if crit_level is not None and isfinite(crit_level) else None,
                ),
                boundaries=result.boundaries,
            )
        else:
            yield result


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
