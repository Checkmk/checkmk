#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)

db2_counters_map = {
    "deadlocks": "Deadlocks",
    "lockwaits": "Lockwaits",
}

type Section = tuple[int | None, Mapping[str, Mapping[str, object]]]


def parse_db2_counters(string_table: StringTable) -> Section:
    dbs: dict[str, dict[str, object]] = {}
    timestamp: int | None = None
    node_infos: list[str] = []
    element_offset: dict[str, int] = {}
    for line in string_table:
        if line[0].startswith("TIMESTAMP"):
            element_offset = {}
            node_infos = []
            # Perl not installed
            timestamp = int(line[1]) if len(line) >= 2 else None
        elif line[1] == "node":
            node_infos.append(" ".join(line[2:]))
        # Some databases run in DPF mode. Means that the database is split over several nodes
        # The counter information also differs for each node. We create one service per DPF node
        elif line[1] in db2_counters_map:
            if node_infos:
                element_offset.setdefault(line[1], 0)
                offset = element_offset[line[1]]
                key = f"{line[0]} DPF {node_infos[offset]}"
                element_offset[line[1]] += 1
            else:
                key = line[0]
            dbs.setdefault(key, {"TIMESTAMP": timestamp})
            dbs[key][line[1]] = line[2]

    # The timestamp is still used for legacy reasons
    # The instance specific timestamp is now available in the dbs
    return timestamp, dbs


agent_section_db2_counters = AgentSection(
    name="db2_counters",
    parse_function=parse_db2_counters,
)


def discover_db2_counters(section: Section) -> DiscoveryResult:
    if len(section) == 2:
        for db in section[1]:
            yield Service(item=db)


def _check_db2_counters(
    value_store: MutableMapping[str, object],
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: Section,
) -> CheckResult:
    default_timestamp = section[0]
    db = section[1].get(item)
    if not db:
        raise IgnoreResultsError("Login into database failed")
    if default_timestamp is None:
        raise IgnoreResultsError("Perl not installed")

    wrapped = False
    timestamp: int = db.get("TIMESTAMP", default_timestamp)  # type: ignore[assignment]
    for counter, label in db2_counters_map.items():
        db_counter: str = db[counter]  # type: ignore[assignment]
        try:
            value = float(db_counter)
        except ValueError:
            yield Result(state=State.CRIT, summary="Invalid value: " + db_counter)
            continue

        try:
            rate = get_rate(value_store, counter, timestamp, value, raise_overflow=True)
        except IgnoreResultsError:
            wrapped = True
            continue

        yield from check_levels(
            value=rate,
            levels_upper=(
                ("fixed", param)
                if (param := params.get(counter)) is not None
                else ("no_levels", None)
            ),
            metric_name=counter,
            render_func=lambda rate: f"{rate:.1f}/s",
            label=label,
        )

    if wrapped:
        raise IgnoreResultsError("Some counter(s) wrapped, no data this time")


def check_db2_counters(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    yield from _check_db2_counters(get_value_store(), item, params, section)


check_plugin_db2_counters = CheckPlugin(
    name="db2_counters",
    service_name="DB2 Counters %s",
    discovery_function=discover_db2_counters,
    check_function=check_db2_counters,
    check_ruleset_name="db2_counters",
    check_default_parameters={},
)
