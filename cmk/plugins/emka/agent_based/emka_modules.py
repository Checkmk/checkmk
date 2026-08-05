#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    OIDBytes,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringByteTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState
from cmk.plugins.lib.humidity import check_humidity, CheckParams
from cmk.plugins.lib.temperature import check_temperature, TempParamType

DETECT_EMKA = all_of(
    contains(".1.3.6.1.2.1.1.1.0", "emka"),
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13595"),
)

# Indices of the four per-component-type value tables (alarm/handle/sensor/relay)
# under ELM2-MIB base .1.3.6.1.4.1.13595.2.2.<index>.1. Shared between the SNMPTree
# fetch definition and the parser below -- both must stay in sync.
_COMPONENT_TABLE_INDICES = ("1", "2", "3", "4")

# basModuleCoIx == 0
_MODULE_TYPES = {
    "0": "vacant",
    "8": "U8, keypad",
    "9": "U9, card module (proximity)",
    "10": "U10, phone module (modem)",
    "11": "U11/U32, up to 8 handles / single point latches",
    "12": "U12/U33, up to 2 handles / single point latches",
    "13": "U13, 4 sensors and 4 relays",
    "14": "U14, communication module",
    "15": "multifunction module M15",
    "16": "multifunction module M16",
}

# independent of module type, basModuleCoIx > 0
_COMPONENT_TABLES = {
    "1": "alarm",
    "2": "handle",
    "3": "sensor",
    "4": "relay",
    "5": "keypad",
    "6": "card_terminal",
    "7": "phone_modem",
    "8": "analogous_output",
}


@dataclass(frozen=True, kw_only=True)
class ModuleComponent:
    type: str
    activation: str


@dataclass(frozen=True, kw_only=True)
class ComponentReading:
    value: str
    mode: str | None = None


@dataclass(frozen=True, kw_only=True)
class SensorReading:
    value: float
    levels: tuple[float, float]
    levels_lower: tuple[float, float]


@dataclass(frozen=True, kw_only=True)
class EmkaSection:
    modules: Mapping[str, ModuleComponent] = field(default_factory=dict)
    alarms: Mapping[str, ComponentReading] = field(default_factory=dict)
    handles: Mapping[str, ComponentReading] = field(default_factory=dict)
    relays: Mapping[str, ComponentReading] = field(default_factory=dict)
    sensors_temp: Mapping[str, SensorReading] = field(default_factory=dict)
    sensors_humid: Mapping[str, SensorReading] = field(default_factory=dict)
    sensors_volt: Mapping[str, SensorReading] = field(default_factory=dict)


def _check_mapped_status(
    reading: ComponentReading, state_map: Mapping[str, tuple[State, str]]
) -> CheckResult:
    state, state_readable = state_map[reading.value]
    yield Result(state=state, summary=f"Status: {state_readable}")


def _parse_scaling_equation(equation_bin: Sequence[int]) -> tuple[str, float, float] | None:
    """Decode an ELM2-MIB sensor scaling equation.

    Format (from ELM2-MIB): Universal: {[factor]}[unit]=$mV*[multiplicator]/[divisor]+[offset]
    [multiplicator], [divisor], [offset] must be integers.
    Example: {0.1}%=$mV*20/100-100
    Default (empty string): {1}mV=$mV*1/1+0

    The device transmits this ASCII-coded with parts separated by null bytes, e.g.
    "=#\xb0C" + NUL + "0.02" + NUL + "-30.0" + NUL decodes to a temperature sensor
    (unit suffix "#\xb0C") scaled by multiplier 0.02 and offset -30.0. May also omit
    the multiplier/offset parts entirely, in which case they default to (1.0, 0.0).
    """
    parts: list[str] = []
    part: list[int] = []
    for byte in equation_bin:
        if byte:
            part.append(byte)
        elif part:
            parts.append("".join(map(chr, part)))
            part = []

    if not parts:
        return None

    if parts[0].endswith("#\xb0C"):
        sensor_ty = "sensor_temp"
    elif parts[0].endswith("#%RF"):
        sensor_ty = "sensor_humid"
    else:
        sensor_ty = "sensor_volt"

    scale_parts = parts[1:]
    if len(scale_parts) == 2:
        multiplier, offset = map(float, scale_parts)
    else:
        multiplier, offset = 1.0, 0.0

    return sensor_ty, multiplier, offset


def parse_emka_modules(string_table: Sequence[StringByteTable]) -> EmkaSection | None:
    if not any(string_table):
        return None

    modules: dict[str, ModuleComponent] = {}
    components: dict[str, dict[str, dict[str, str]]] = {
        "alarm": {},
        "handle": {},
        "sensor": {},
        "relay": {},
    }

    for oidend, status, ty, mod_info, remark in string_table[0]:
        oidend, status, ty, mod_info, remark = (
            str(oidend),
            str(status),
            str(ty),
            str(mod_info),
            str(remark),
        )
        mo_index, co_index = oidend.split(".")
        if mo_index == "0":
            itemname = f"Master {mod_info.split(',')[0]}"
        else:
            itemname = f"Perip {mo_index} {mod_info}"

        if co_index == "0":
            modules.setdefault(
                itemname.strip(),
                # NOTE: "type" is indexed by co_index (always "0" in this branch),
                # not the fetched module-type code `ty` -- this reproduces a known
                # bug (module type always reports "vacant"), tracked for a
                # follow-up fix rather than changed here.
                ModuleComponent(type=_MODULE_TYPES[co_index], activation=status),
            )
            continue

        table = _COMPONENT_TABLES[ty]
        itemname = oidend if remark == "" else f"{remark} {oidend}"
        if table in components:
            components[table].setdefault(itemname, {"_location_": oidend})

    for table_idx, block in zip(_COMPONENT_TABLE_INDICES, string_table[1:5]):
        table = _COMPONENT_TABLES[table_idx]
        for module_link, value, mode in block:
            module_link, value, mode = str(module_link), str(value), str(mode)
            location = ".".join(module_link.split(".")[-2:])
            for attrs in components[table].values():
                if attrs["_location_"] != location:
                    continue
                attrs["value"] = value
                if mode:
                    attrs["mode"] = mode

    for oidend, threshold in string_table[5]:
        oidend, threshold = str(oidend), str(threshold)
        location, threshold_ty = oidend.split(".")
        key = "levels_lower" if threshold_ty == "1" else "levels"
        for attrs in components["sensor"].values():
            if attrs["_location_"].startswith(f"{location}."):
                attrs[key] = (threshold, threshold)  # type: ignore[assignment]

    sensors: dict[str, dict[str, SensorReading]] = {
        "sensor_temp": {},
        "sensor_humid": {},
        "sensor_volt": {},
    }
    for row in string_table[6]:
        oidend = str(row[0])
        equation_bin = row[1]
        if isinstance(equation_bin, str):
            continue
        decoded = _parse_scaling_equation(equation_bin)
        if decoded is None:
            continue
        sensor_ty, multiplier, offset = decoded

        def scale_f(x: str | float, m: float = multiplier, a: float = offset) -> float:
            return float(x) * m + a

        location = str(chr(int(oidend.split(".", 1)[0])))
        for sensor, attrs in components["sensor"].items():
            if not attrs["_location_"].endswith(f".{location}"):
                continue
            if "value" not in attrs or "levels" not in attrs or "levels_lower" not in attrs:
                break
            sensors[sensor_ty].setdefault(
                sensor,
                SensorReading(
                    value=scale_f(attrs["value"]),
                    levels=(scale_f(attrs["levels"][0]), scale_f(attrs["levels"][1])),
                    levels_lower=(
                        scale_f(attrs["levels_lower"][0]),
                        scale_f(attrs["levels_lower"][1]),
                    ),
                ),
            )
            break

    def readings(table: str) -> dict[str, ComponentReading]:
        return {
            name: ComponentReading(value=attrs["value"], mode=attrs.get("mode"))
            for name, attrs in components[table].items()
            if "value" in attrs
        }

    return EmkaSection(
        modules=modules,
        alarms=readings("alarm"),
        handles=readings("handle"),
        relays=readings("relay"),
        sensors_temp=sensors["sensor_temp"],
        sensors_humid=sensors["sensor_humid"],
        sensors_volt=sensors["sensor_volt"],
    )


_ACTIVATION_STATES = {
    "-": (State.OK, "vacant"),
    "?": (State.OK, "detect modus"),
    "x": (State.OK, "excluded"),
    "e": (State.CRIT, "error"),
    "c": (State.CRIT, "collision detected"),
    "w": (State.WARN, "wait for dynamic address"),
    "P": (State.WARN, "polling"),
    "i": (State.OK, "inactive"),
    "t": (State.CRIT, "timeout"),
    "T": (State.CRIT, "timeout alarm"),
    "A": (State.CRIT, "alarm active"),
    "L": (State.OK, "alarm latched"),
    "#": (State.OK, "OK"),
}


def discover_emka_modules(section: EmkaSection) -> DiscoveryResult:
    for entry, module in section.modules.items():
        if module.activation != "i":
            yield Service(item=entry)


def check_emka_modules(item: str, section: EmkaSection) -> CheckResult:
    module = section.modules.get(item)
    if module is None:
        return
    state, state_readable = _ACTIVATION_STATES[module.activation]
    yield Result(
        state=state,
        summary=f"Activation status: {state_readable}, Type: {module.type}",
    )


_ALARM_STATES = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.OK, "inactive"),
    "3": (State.CRIT, "active"),
    "4": (State.OK, "latched"),
}


def discover_emka_modules_alarm(section: EmkaSection) -> DiscoveryResult:
    for entry, alarm in section.alarms.items():
        if alarm.value != "2":
            yield Service(item=entry)


def check_emka_modules_alarm(item: str, section: EmkaSection) -> CheckResult:
    alarm = section.alarms.get(item)
    if alarm is None:
        return
    yield from _check_mapped_status(alarm, _ALARM_STATES)


_HANDLE_STATES = {
    "1": (State.OK, "closed"),
    "2": (State.WARN, "opened"),
    "3": (State.UNKNOWN, "unlocked"),
    "4": (State.UNKNOWN, "delay"),
    "5": (State.CRIT, "open time ex"),
}


def discover_emka_modules_handle(section: EmkaSection) -> DiscoveryResult:
    for entry in section.handles:
        yield Service(item=entry)


def check_emka_modules_handle(item: str, section: EmkaSection) -> CheckResult:
    handle = section.handles.get(item)
    if handle is None:
        return
    yield from _check_mapped_status(handle, _HANDLE_STATES)


_RELAY_STATES = {
    "1": (State.OK, "off"),
    "2": (State.OK, "on"),
}


def discover_emka_modules_relay(section: EmkaSection) -> DiscoveryResult:
    for entry, relay in section.relays.items():
        if relay.value != "1":
            yield Service(item=entry)


def check_emka_modules_relay(item: str, section: EmkaSection) -> CheckResult:
    relay = section.relays.get(item)
    if relay is None:
        return
    yield from _check_mapped_status(relay, _RELAY_STATES)


def discover_emka_modules_sensor_humid(section: EmkaSection) -> DiscoveryResult:
    for entry in section.sensors_humid:
        yield Service(item=entry)


def check_emka_modules_sensor_humid(
    item: str, params: CheckParams, section: EmkaSection
) -> CheckResult:
    sensor = section.sensors_humid.get(item)
    if sensor is None:
        return
    yield from check_humidity(sensor.value, params)


def discover_emka_modules_sensor_temp(section: EmkaSection) -> DiscoveryResult:
    for entry in section.sensors_temp:
        yield Service(item=entry)


def check_emka_modules_sensor_temp(
    item: str, params: TempParamType, section: EmkaSection
) -> CheckResult:
    sensor = section.sensors_temp.get(item)
    if sensor is None:
        return
    yield from check_temperature(
        reading=sensor.value,
        params=params,
        unique_name=f"emka_modules_sensor_temp.{item}",
        value_store=get_value_store(),
        dev_levels=sensor.levels,
        dev_levels_lower=sensor.levels_lower,
    )


def discover_emka_modules_sensor_volt(section: EmkaSection) -> DiscoveryResult:
    for entry in section.sensors_volt:
        yield Service(item=entry)


def check_emka_modules_sensor_volt(
    item: str, params: Mapping[str, object], section: EmkaSection
) -> CheckResult:
    sensor = section.sensors_volt.get(item)
    if sensor is None:
        return
    value = sensor.value / 1000.0
    yield from check_elphase(
        params,
        ElPhase(voltage=ReadingWithState(value=value)),
    )


snmp_section_emka_modules = SNMPSection(
    name="emka_modules",
    detect=DETECT_EMKA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13595.2.1.3.3.1",
            oids=[OIDEnd(), "3", "4", "5", "7"],
        ),
        *(
            SNMPTree(
                base=f".1.3.6.1.4.1.13595.2.2.{table}.1",
                oids=[
                    "3",  # ELM2-MIB::coHandleModuleLink
                    "4",  # ELM2-MIB::co*[Status/Value]
                    "15",  # ELM2-MIB::coSensorMode
                ],
            )
            for table in _COMPONENT_TABLE_INDICES
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13595.2.2.3.1",
            oids=[OIDEnd(), "7"],  # ELM2-MIB::coSensorThreshold
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13595.2.2.3.1",
            oids=[OIDEnd(), OIDBytes("18")],  # ELM2-MIB::coSensorUnitEquation
        ),
    ],
    parse_function=parse_emka_modules,
)


check_plugin_emka_modules = CheckPlugin(
    name="emka_modules",
    service_name="Module %s",
    discovery_function=discover_emka_modules,
    check_function=check_emka_modules,
)

check_plugin_emka_modules_alarm = CheckPlugin(
    name="emka_modules_alarm",
    service_name="Alarm %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_alarm,
    check_function=check_emka_modules_alarm,
)

check_plugin_emka_modules_handle = CheckPlugin(
    name="emka_modules_handle",
    service_name="Handle %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_handle,
    check_function=check_emka_modules_handle,
)

check_plugin_emka_modules_relay = CheckPlugin(
    name="emka_modules_relay",
    service_name="Relay %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_relay,
    check_function=check_emka_modules_relay,
)

check_plugin_emka_modules_sensor_humid = CheckPlugin(
    name="emka_modules_sensor_humid",
    service_name="Humidity %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_sensor_humid,
    check_function=check_emka_modules_sensor_humid,
    check_ruleset_name="humidity",
    check_default_parameters={},
)

check_plugin_emka_modules_sensor_temp = CheckPlugin(
    name="emka_modules_sensor_temp",
    service_name="Temperature %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_sensor_temp,
    check_function=check_emka_modules_sensor_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)

check_plugin_emka_modules_sensor_volt = CheckPlugin(
    name="emka_modules_sensor_volt",
    service_name="Phase %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_sensor_volt,
    check_function=check_emka_modules_sensor_volt,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
