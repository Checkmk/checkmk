#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Generator, Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# very odd and confusing example outputs:

# version 3.0.0
# .1.3.6.1.4.1.21239.5.1.1.2.0 3.0.0
# .1.3.6.1.4.1.21239.5.1.1.7.0 1
# .1.3.6.1.4.1.21239.5.1.2.1.3.1 Data Center 1
# .1.3.6.1.4.1.21239.5.1.2.1.5.1 1
# .1.3.6.1.4.1.21239.5.1.2.1.4.1 "91 54 06 9D C9 54 06 9D E9 C9 06 9D BD 9B 06 9D "
# .1.3.6.1.4.1.21239.5.1.2.1.6.1 199
# .1.3.6.1.4.1.21239.5.1.2.1.7.1 36
# .1.3.6.1.4.1.21239.5.1.2.1.8.1 44
#
# version 3.2.0
# .1.3.6.1.4.1.21239.5.1.1.2.0 3.2.0
# .1.3.6.1.4.1.21239.5.1.1.7.0 1
# .1.3.6.1.4.1.21239.5.1.2.1.1.1 1
# .1.3.6.1.4.1.21239.5.1.2.1.2.1 41D88039003580C3
# .1.3.6.1.4.1.21239.5.1.2.1.3.1 RSGLDN Watchdog 15
# .1.3.6.1.4.1.21239.5.1.2.1.4.1 1
# .1.3.6.1.4.1.21239.5.1.2.1.5.1 173
# .1.3.6.1.4.1.21239.5.1.2.1.6.1 46
# .1.3.6.1.4.1.21239.5.1.2.1.7.1 56

Section = dict[str, dict[str, Any]]

_AVAILABILITY_MAP: Mapping[str, tuple[State, str]] = {
    "0": (State.CRIT, "unavailable"),
    "1": (State.OK, "available"),
    "2": (State.WARN, "partially unavailable"),
}


def _parse_legacy_line(
    line: Sequence[str], temp_unit: str
) -> Generator[tuple[str, dict[str, Any]]]:
    """
    >>> [i for i in _parse_legacy_line(['1', 'blah', '2CD', '1', '30', '20', '8'], 'C')]
    [('general', {'Watchdog 1': {'descr': 'blah', 'availability': ('1',)}}), ('temp', {'Temperature 1': ('30', 'C')}), ('humidity', {'Humidity 1': '20'}), ('dew', {'Dew point 1': ('8', 'C')})]
    """
    sensor_id = line[0]
    yield (
        "general",
        {
            f"Watchdog {sensor_id}": {
                "descr": line[1],
                "availability": (line[3],),
            },
        },
    )
    yield "temp", {f"Temperature {sensor_id}": (line[4], temp_unit)}
    yield "humidity", {f"Humidity {sensor_id}": line[5]}
    yield "dew", {f"Dew point {sensor_id}": (line[6], temp_unit)}


def _parse_line(line: Sequence[str], temp_unit: str) -> Generator[tuple[str, dict[str, Any]]]:
    """
    >>> [i for i in _parse_line(['1', 'blah', '1', '30', '20', '8'], 'C')]
    [('general', {'Watchdog 1': {'descr': 'blah', 'availability': ('1',)}}), ('temp', {'Temperature 1': ('30', 'C')}), ('humidity', {'Humidity 1': '20'}), ('dew', {'Dew point 1': ('8', 'C')})]
    """
    sensor_id = line[0]
    yield (
        "general",
        {
            f"Watchdog {sensor_id}": {
                "descr": line[1],
                "availability": (line[2],),
            },
        },
    )
    yield "temp", {f"Temperature {sensor_id}": (line[3], temp_unit)}
    yield "humidity", {f"Humidity {sensor_id}": line[4]}
    yield "dew", {f"Dew point {sensor_id}": (line[5], temp_unit)}


def parse_watchdog_sensors(string_table: Sequence[StringTable]) -> Section:
    parsed: Section = {}

    general, data = string_table
    if not general:
        return parsed

    temp_unit = {
        "1": "C",
        "0": "F",
        "": "C",
    }[general[0][1]]

    version = int(general[0][0].replace(".", ""))

    line_parser = _parse_legacy_line if version <= 300 else _parse_line

    for line in data:
        for sensor_type, parsed_line in line_parser(line, temp_unit):
            parsed.setdefault(sensor_type, {}).update(parsed_line)

    return parsed


# .
#   .--general-------------------------------------------------------------


def discover_watchdog_sensors(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section.get("general", {}))


def check_watchdog_sensors(item: str, section: Section) -> CheckResult:
    data = section.get("general", {}).get(item)

    if not data:
        return

    descr = data["descr"]
    (availability_raw,) = data["availability"]
    state, state_readable = _AVAILABILITY_MAP[availability_raw]

    yield Result(state=state, summary=state_readable)

    if descr != "":
        yield Result(state=State.OK, summary=f"Location: {descr}")


snmp_section_watchdog_sensors = SNMPSection(
    name="watchdog_sensors",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21239.5.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21239.42.1"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.21239.5.1.1",
            oids=["2", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.21239.5.1.2.1",
            oids=[OIDEnd(), "3", "4", "5", "6", "7", "8"],
        ),
    ],
    parse_function=parse_watchdog_sensors,
)

check_plugin_watchdog_sensors = CheckPlugin(
    name="watchdog_sensors",
    service_name="%s",
    discovery_function=discover_watchdog_sensors,
    check_function=check_watchdog_sensors,
)

# .
#   .--temp----------------------------------------------------------------


def discover_watchdog_sensors_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section.get("temp", {}))


def check_watchdog_sensors_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    data = section.get("temp", {}).get(item)

    if not data:
        return

    temperature_str, unit = data
    yield from check_temperature(
        reading=float(temperature_str) / 10.0,
        params=params,
        unique_name=f"check_watchdog_sensors.{item}",
        value_store=get_value_store(),
        dev_unit=unit.lower(),
    )


check_plugin_watchdog_sensors_temp = CheckPlugin(
    name="watchdog_sensors_temp",
    service_name="%s ",
    sections=["watchdog_sensors"],
    discovery_function=discover_watchdog_sensors_temp,
    check_function=check_watchdog_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)

# .
#   .--humidity------------------------------------------------------------


def discover_watchdog_sensors_humidity(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section.get("humidity", {}))


def check_watchdog_sensors_humidity(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    data = section.get("humidity", {}).get(item)

    if not data:
        return

    humidity = int(data)
    warn, crit = params["levels"]
    warn_lower, crit_lower = params["levels_lower"]

    if not (crit_lower < humidity < crit):
        state = State.CRIT
    elif not (warn_lower < humidity < warn):
        state = State.WARN
    else:
        state = State.OK

    summary = f"{humidity:.1f}%"
    if state is not State.OK:
        summary += (
            f" (warn/crit at {warn}/{crit})"
            if humidity >= warn
            else f" (warn/crit below {warn_lower}/{crit_lower})"
        )

    yield Result(state=state, summary=summary)
    yield Metric("humidity", humidity, levels=(warn, crit))


check_plugin_watchdog_sensors_humidity = CheckPlugin(
    name="watchdog_sensors_humidity",
    service_name="%s",
    sections=["watchdog_sensors"],
    discovery_function=discover_watchdog_sensors_humidity,
    check_function=check_watchdog_sensors_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (50.0, 55.0),
        "levels_lower": (10.0, 15.0),
    },
)

# .
#   .--dew-----------------------------------------------------------------


def discover_watchdog_sensors_dew(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section.get("dew", {}))


def check_watchdog_sensors_dew(item: str, params: TempParamType, section: Section) -> CheckResult:
    data = section.get("dew", {}).get(item)

    if not data:
        return

    dew = float(data[0]) / 10.0
    unit = data[1]
    if unit == "F":
        dew = 5.0 / 9.0 * (dew - 32)
    yield from check_temperature(
        reading=dew,
        params=params,
        unique_name=f"check_watchdog_sensors.{item}",
        value_store=get_value_store(),
    )


check_plugin_watchdog_sensors_dew = CheckPlugin(
    name="watchdog_sensors_dew",
    service_name="%s",
    sections=["watchdog_sensors"],
    discovery_function=discover_watchdog_sensors_dew,
    check_function=check_watchdog_sensors_dew,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
