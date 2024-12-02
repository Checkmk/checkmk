#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
    StringTable,
)

_counter_to_var = {
    "i/o database reads (attached) average latency": "read_attached_latency_s",
    "i/o database reads (recovery) average latency": "read_recovery_latency_s",
    "i/o database writes (attached) average latency": "write_latency_s",
    "i/o log writes average latency": "log_latency_s",
    "e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (angef\x81gt)": "read_attached_latency_s",
    "e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (wiederherstellung)": "read_recovery_latency_s",
    "e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (angef\x81gt)": "write_latency_s",
    "e/a: durchschnittliche wartezeit f\x81r protokollschreiboperationen": "log_latency_s",
}


@dataclass(frozen=True)
class DbPerfData:
    read_attached_latency_s: float | None = None
    read_recovery_latency_s: float | None = None
    write_latency_s: float | None = None
    log_latency_s: float | None = None


def _delocalize_de_DE(value: str) -> str:
    # replace localized thousands-/ decimal-separators
    return value.replace(".", "").replace(",", ".")


Section = Mapping[str, DbPerfData]


def parse_msexch_database(string_table: StringTable) -> Section:
    if not (string_table and string_table[0]):
        return {}

    delocalize_func = None
    offset = 0
    if len(string_table[0]) > 1 and string_table[0][0] == "locale":
        locale = string_table[0][1].strip()
        offset = 1
        delocalize_func = {
            "de-DE": _delocalize_de_DE,
        }.get(locale)

    parsed: dict[str, dict[str, float]] = {}
    for row in string_table[offset:]:
        row = [r.strip('"') for r in row]
        if len(row) != 2 or not row[0].startswith("\\\\"):
            continue

        __, obj, counter = row[0].rsplit("\\", 2)

        try:
            var = _counter_to_var[counter]
        except KeyError:
            continue

        instance = obj.split("(", 1)[-1].split(")", 1)[0]
        value = row[1]

        if delocalize_func is not None:
            value = delocalize_func(value)

        # The entries for log verifier contain an ID as the last part
        # which changes upon reboot of the exchange server. Therefore,
        # we just remove them here as a workaround.
        if "/log verifier" in instance:
            instance = instance.rsplit(" ", 1)[0]

        try:
            parsed.setdefault(instance, {})[var] = float(value) / 1000.0
        except ValueError:
            continue

    return {item: DbPerfData(**values) for item, values in parsed.items() if values}


def inventory_msexch_database(section: Section) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


class Params(TypedDict):
    read_attached_latency_s: LevelsT[float]
    read_recovery_latency_s: LevelsT[float]
    write_latency_s: LevelsT[float]
    log_latency_s: LevelsT[float]


def check_msexch_database(item: str, params: Params, section: Section) -> CheckResult:
    try:
        data = section[item]
    except KeyError:
        return

    if data.read_attached_latency_s is not None:
        yield from check_levels(
            data.read_attached_latency_s,
            metric_name="db_read_latency_s",
            levels_upper=params["read_attached_latency_s"],
            label="DB read (attached) latency",
            render_func=render.timespan,
        )

    if data.read_recovery_latency_s is not None:
        yield from check_levels(
            data.read_recovery_latency_s,
            metric_name="db_read_recovery_latency_s",
            levels_upper=params["read_recovery_latency_s"],
            label="DB read (recovery) latency",
            render_func=render.timespan,
        )

    if data.write_latency_s is not None:
        yield from check_levels(
            data.write_latency_s,
            metric_name="db_write_latency_s",
            levels_upper=params["write_latency_s"],
            label="DB write (attached) latency",
            render_func=render.timespan,
        )

    if data.log_latency_s is not None:
        yield from check_levels(
            data.log_latency_s,
            metric_name="db_log_latency_s",
            levels_upper=params["log_latency_s"],
            label="Log latency",
            render_func=render.timespan,
        )


agent_section_msexch_database = AgentSection(
    name="msexch_database",
    parse_function=parse_msexch_database,
)

check_plugin_msexch_database = CheckPlugin(
    name="msexch_database",
    service_name="Exchange Database %s",
    discovery_function=inventory_msexch_database,
    check_function=check_msexch_database,
    check_ruleset_name="msx_database",
    check_default_parameters=Params(
        read_attached_latency_s=("fixed", (0.2, 0.25)),
        read_recovery_latency_s=("fixed", (0.15, 0.2)),
        write_latency_s=("fixed", (0.04, 0.05)),
        log_latency_s=("fixed", (0.005, 0.01)),
    ),
)
