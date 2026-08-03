#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Section = Sequence[StringTable]


def parse_wagner_titanus_topsense(
    string_table: Sequence[StringTable],
) -> Section | None:
    return string_table if string_table[0] else None


snmp_section_wagner_titanus_topsense = SNMPSection(
    name="wagner_titanus_topsense",
    parse_function=parse_wagner_titanus_topsense,
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.34187.21501"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.34187.74195"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.1",
            oids=["1", "3", "4", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34187.21501.1.1",
            oids=["1", "2", "3", "1000", "1001", "1002", "1003", "1004", "1005", "1006"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34187.21501.2.1",
            oids=[
                "245810000",
                "245820000",
                "245950000",
                "246090000",
                "245960000",
                "246100000",
                "245970000",
                "246110000",
                "24584008",
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34187.74195.1.1",
            oids=["1", "2", "3", "1000", "1001", "1002", "1003", "1004", "1005", "1006"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34187.74195.2.1",
            oids=[
                "245790000",
                "245800000",
                "245940000",
                "246060000",
                "245950000",
                "246070000",
                "245960000",
                "246080000",
            ],
        ),
    ],
)


def _get_model_data(section: Section) -> list[StringTable]:
    # not much of a parse function. simply retrieves the info blocks that apply for the
    # respective topsens model and returns only those
    return [section[0], section[1] or section[3], section[2] or section[4]]


#   .--titanus info--------------------------------------------------------


def discover_wagner_titanus_topsense_info(section: Section) -> DiscoveryResult:
    yield Service()


def check_wagner_titanus_topsense_info(section: Section) -> CheckResult:
    parsed = _get_model_data(section)
    message = f"System: {parsed[0][0][0]}"
    message += f", Uptime: {render.timespan(int(parsed[0][0][1]) // 100)}"
    message += f", System Name: {parsed[0][0][3]}"
    message += f", System Contact: {parsed[0][0][2]}"
    message += f", System Location: {parsed[0][0][4]}"
    message += f", Company: {parsed[1][0][0]}"
    message += f", Model: {parsed[1][0][1]}"
    message += f", Revision: {parsed[1][0][2]}"
    if len(section) > 8:
        ts_lsn_bus = parsed[2][0][8]
        if ts_lsn_bus == "0":
            ts_lsn_bus = "offline"
        elif ts_lsn_bus == "1":
            ts_lsn_bus = "online"
        else:
            ts_lsn_bus = "unknown"

        message += f", LSNi bus: {ts_lsn_bus}"
    yield Result(state=State.OK, summary=message)


check_plugin_wagner_titanus_topsense_info = CheckPlugin(
    name="wagner_titanus_topsense_info",
    service_name="Topsense Info",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_info,
    check_function=check_wagner_titanus_topsense_info,
)

# .
#   .--overall status------------------------------------------------------


def discover_wagner_titanus_topsense_overall_status(section: Section) -> DiscoveryResult:
    yield Service()


def check_wagner_titanus_topsense_overall_status(section: Section) -> CheckResult:
    parsed = _get_model_data(section)
    psw_failure = parsed[1][0][9]
    if psw_failure == "0":
        yield Result(state=State.OK, summary="Overall Status reports OK")
    else:
        yield Result(state=State.CRIT, summary="Overall Status reports a problem")


check_plugin_wagner_titanus_topsense_overall_status = CheckPlugin(
    name="wagner_titanus_topsense_overall_status",
    service_name="Overall Status",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_overall_status,
    check_function=check_wagner_titanus_topsense_overall_status,
)

# .
#   .--alarm---------------------------------------------------------------


def discover_wagner_titanus_topsense_alarm(section: Section) -> DiscoveryResult:
    yield Service(item="1")
    yield Service(item="2")


def check_wagner_titanus_topsense_alarm(item: str, section: Section) -> CheckResult:
    parsed = _get_model_data(section)
    if item == "1":
        main_alarm = parsed[1][0][3]
        pre_alarm = parsed[1][0][4]
        info_alarm = parsed[1][0][5]
    elif item == "2":
        main_alarm = parsed[1][0][6]
        pre_alarm = parsed[1][0][7]
        info_alarm = parsed[1][0][8]
    else:
        yield Result(state=State.UNKNOWN, summary=f"Alarm Detector {item} not found in SNMP")
        return

    state = State.OK
    message = "No Alarm"
    if info_alarm != "0":
        message = "Info Alarm"
        state = State.WARN
    if pre_alarm != "0":
        message = "Pre Alarm"
        state = State.WARN
    if main_alarm != "0":
        message = "Main Alarm: Fire"
        state = State.CRIT

    yield Result(state=state, summary=message)


check_plugin_wagner_titanus_topsense_alarm = CheckPlugin(
    name="wagner_titanus_topsense_alarm",
    service_name="Alarm Detector %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_alarm,
    check_function=check_wagner_titanus_topsense_alarm,
)

# .
#   .--smoke percent-------------------------------------------------------


def discover_wagner_titanus_topsense_smoke(section: Section) -> DiscoveryResult:
    yield Service(item="1")
    yield Service(item="2")


def check_wagner_titanus_topsense_smoke(item: str, section: Section) -> CheckResult:
    parsed = _get_model_data(section)
    if item == "1":
        smoke_perc = float(parsed[2][0][0])
    elif item == "2":
        smoke_perc = float(parsed[2][0][1])
    else:
        yield Result(state=State.UNKNOWN, summary=f"Smoke Detector {item} not found in SNMP")
        return

    if smoke_perc > 5:
        state = State.CRIT
    elif smoke_perc > 3:
        state = State.WARN
    else:
        state = State.OK

    yield Result(state=state, summary=f"{smoke_perc:0.6f}% smoke detected")
    yield Metric("smoke_perc", smoke_perc)


check_plugin_wagner_titanus_topsense_smoke = CheckPlugin(
    name="wagner_titanus_topsense_smoke",
    service_name="Smoke Detector %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_smoke,
    check_function=check_wagner_titanus_topsense_smoke,
)

# .
#   .--chamber deviation---------------------------------------------------


def discover_wagner_titanus_topsense_chamber_deviation(section: Section) -> DiscoveryResult:
    yield Service(item="1")
    yield Service(item="2")


def check_wagner_titanus_topsense_chamber_deviation(item: str, section: Section) -> CheckResult:
    parsed = _get_model_data(section)
    if item == "1":
        chamber_deviation = float(parsed[2][0][2])
    elif item == "2":
        chamber_deviation = float(parsed[2][0][3])
    else:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Chamber Deviation Detector {item} not found in SNMP",
        )
        return

    yield Result(state=State.OK, summary=f"{chamber_deviation:0.6f}% Chamber Deviation")
    yield Metric("chamber_deviation", chamber_deviation)


check_plugin_wagner_titanus_topsense_chamber_deviation = CheckPlugin(
    name="wagner_titanus_topsense_chamber_deviation",
    service_name="Chamber Deviation Detector %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_chamber_deviation,
    check_function=check_wagner_titanus_topsense_chamber_deviation,
)

# .
#   .--air flow deviation--------------------------------------------------


def discover_wagner_titanus_topsense_airflow_deviation(section: Section) -> DiscoveryResult:
    yield Service(item="1")
    yield Service(item="2")


def check_wagner_titanus_topsense_airflow_deviation(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    parsed = _get_model_data(section)
    if item == "1":
        airflow_deviation = float(parsed[2][0][4])
    elif item == "2":
        airflow_deviation = float(parsed[2][0][5])
    else:
        return

    yield from check_levels(
        airflow_deviation,
        metric_name="airflow_deviation",
        levels_upper=params["levels_upper"],
        levels_lower=params["levels_lower"],
        render_func=lambda v: f"{v:0.6f}%",
        label="Airflow deviation",
    )


check_plugin_wagner_titanus_topsense_airflow_deviation = CheckPlugin(
    name="wagner_titanus_topsense_airflow_deviation",
    service_name="Airflow Deviation Detector %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_airflow_deviation,
    check_function=check_wagner_titanus_topsense_airflow_deviation,
    check_ruleset_name="airflow_deviation",
    check_default_parameters={
        "levels_upper": (20.0, 20.0),
        "levels_lower": (-20.0, -20.0),
    },
)

# .
#   .--air temp------------------------------------------------------------


def discover_wagner_titanus_topsense_temp(section: Section) -> DiscoveryResult:
    yield Service(item="Ambient 1")
    yield Service(item="Ambient 2")


def check_wagner_titanus_topsense_temp(
    item: str, params: TempParamType, section: Section
) -> CheckResult:
    parsed = _get_model_data(section)
    if not item.startswith("Ambient"):
        item = f"Ambient {item}"

    if item == "Ambient 1":
        temp = float(parsed[2][0][6])
    elif item == "Ambient 2":
        temp = float(parsed[2][0][7])
    else:
        return

    yield from check_temperature(
        reading=temp,
        params=params,
        unique_name=f"wagner_titanus_topsense_{item}",
        value_store=get_value_store(),
    )


check_plugin_wagner_titanus_topsense_temp = CheckPlugin(
    name="wagner_titanus_topsense_temp",
    service_name="Temperature %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_temp,
    check_function=check_wagner_titanus_topsense_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)

# .
