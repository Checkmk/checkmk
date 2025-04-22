#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import TypedDict

from cmk.agent_based.v1 import GetRateError
from cmk.agent_based.v2 import (
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    LevelsT,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)


class OperationStatCheckParamT(TypedDict):
    error_rate: LevelsT
    request_rate: LevelsT
    operation_errors: LevelsT


class EventStatCheckParamT(TypedDict):
    critical_events: LevelsT
    noncritical_events: LevelsT
    critical_event_rate: LevelsT
    noncritical_event_rate: LevelsT


CheckParamT = OperationStatCheckParamT | EventStatCheckParamT


class Section(TypedDict):
    operation_requests: int
    operation_errors: int
    critical_events: int
    noncritical_events: int


def _check_values(key: str, label: str, section: Section, params: CheckParamT) -> CheckResult:
    events = section[key]  # type:ignore[literal-required]

    yield from check_levels(
        events,
        label=label,
        metric_name=key,
        levels_upper=params[key],  # type:ignore[literal-required]
        render_func=lambda v: f"{v} {label} since last reset",
    )


def _check_rates(
    metric_name: str, param_name: str, label: str, now: float, section: Section, params: CheckParamT
) -> CheckResult:
    events = section[metric_name]  # type:ignore[literal-required]
    event_rate = get_rate(get_value_store(), param_name, now, events, raise_overflow=True)

    yield from check_levels(
        event_rate,
        label=label,
        metric_name=metric_name,
        levels_upper=params[param_name],  # type:ignore[literal-required]
        render_func=lambda v: f"{v:.2f} {label}/s",
    )


def parse_safenet_hsm(string_table: StringTable) -> Section | None:
    return (
        Section(
            operation_requests=int(string_table[0][0]),
            operation_errors=int(string_table[0][1]),
            critical_events=int(string_table[0][2]),
            noncritical_events=int(string_table[0][3]),
        )
        if string_table
        else None
    )


# .
#   .--Event stats---------------------------------------------------------.
#   |          _____                 _         _        _                  |
#   |         | ____|_   _____ _ __ | |_   ___| |_ __ _| |_ ___            |
#   |         |  _| \ \ / / _ \ '_ \| __| / __| __/ _` | __/ __|           |
#   |         | |___ \ V /  __/ | | | |_  \__ \ || (_| | |_\__ \           |
#   |         |_____| \_/ \___|_| |_|\__| |___/\__\__,_|\__|___/           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_hsm_events(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_safenet_hsm_events(params: EventStatCheckParamT, section: Section) -> CheckResult:
    now = time.time()
    errors: list[str] = []

    for event in ("critical", "noncritical"):
        yield from _check_values(f"{event}_events", f"{event.title()} Events", section, params)
        try:
            yield from _check_rates(
                f"{event}_events",
                f"{event}_event_rate",
                f"{event.title()} Events",
                now,
                section,
                params,
            )
        except GetRateError:
            errors.extend(f"{event}_events")
    if errors:
        raise GetRateError(
            f"Counter {', '.join(errors)} has been initialized. Result available on second check execution."
        )


check_plugin_safenet_hsm_events = CheckPlugin(
    name="safenet_hsm_events",
    service_name="HSM Safenet Event Stats",
    sections=["safenet_hsm"],
    discovery_function=inventory_safenet_hsm_events,
    check_function=check_safenet_hsm_events,
    check_ruleset_name="safenet_hsm_eventstats",
    check_default_parameters=EventStatCheckParamT(
        critical_events=("no_levels", None),
        noncritical_events=("no_levels", None),
        critical_event_rate=("no_levels", None),
        noncritical_event_rate=("no_levels", None),
    ),
)


# .
#   .--Operation stats-----------------------------------------------------.
#   |             ___                       _   _                          |
#   |            / _ \ _ __   ___ _ __ __ _| |_(_) ___  _ __               |
#   |           | | | | '_ \ / _ \ '__/ _` | __| |/ _ \| '_ \              |
#   |           | |_| | |_) |  __/ | | (_| | |_| | (_) | | | |             |
#   |            \___/| .__/ \___|_|  \__,_|\__|_|\___/|_| |_|             |
#   |                 |_|                                                  |
#   |                            _        _                                |
#   |                        ___| |_ __ _| |_ ___                          |
#   |                       / __| __/ _` | __/ __|                         |
#   |                       \__ \ || (_| | |_\__ \                         |
#   |                       |___/\__\__,_|\__|___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_hsm(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_safenet_hsm(params: OperationStatCheckParamT, section: Section) -> CheckResult:
    now = time.time()
    error = False

    yield from _check_values("operation_errors", "Errors", section, params)

    try:
        yield from _check_rates("operation_errors", "error_rate", "Errors", now, section, params)
    except GetRateError:
        error = True

    try:
        yield from _check_rates(
            "operation_requests", "request_rate", "Requests", now, section, params
        )
    except GetRateError:
        error = True

    if error:
        raise GetRateError(
            "Counters have been initialized. Result available on second check execution."
        )


check_plugin_safenet_hsm = CheckPlugin(
    name="safenet_hsm",
    service_name="HSM Operation Stats",
    sections=["safenet_hsm"],
    discovery_function=inventory_safenet_hsm,
    check_function=check_safenet_hsm,
    check_ruleset_name="safenet_hsm_operstats",
    check_default_parameters=OperationStatCheckParamT(
        error_rate=("no_levels", None),
        request_rate=("no_levels", None),
        operation_errors=("no_levels", None),
    ),
)

snmp_section_safenet_hsm = SimpleSNMPSection(
    name="safenet_hsm",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12383"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12383.3.1.1",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_safenet_hsm,
)
