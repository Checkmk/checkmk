#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<mkeventd_status:sep(0)>>>
# ["heute"]
# [["status_config_load_time", "status_num_open_events", "status_messages", "status_message_rate", "status_average_message_rate", "status_connects", "status_connect_rate", "status_average_connect_rate", "status_rule_tries", "status_rule_trie_rate", "status_average_rule_trie_rate", "status_drops", "status_drop_rate", "status_average_drop_rate", "status_events", "status_event_rate", "status_average_event_rate", "status_rule_hits", "status_rule_hit_rate", "status_average_rule_hit_rate", "status_average_processing_time", "status_average_request_time", "status_average_sync_time", "status_replication_slavemode", "status_replication_last_sync", "status_replication_success", "status_event_limit_host", "status_event_limit_rule", "status_event_limit_overall", "status_event_limit_active_hosts", "status_event_limit_active_rules", "status_event_limit_active_overall"], [1474040901.678517, 19, 0, 0.0, 0.0, 2, 0.1998879393337847, 0.1998879393337847, 0, 0.0, 0.0, 0, 0.0, 0.0, 0, 0.0, 0.0, 0, 0.0, 0.0, 0.0, 0.002389192581176758, 0.0, "master", 0.0, false, 10, 5, 20, [], ["catch_w", "catch_y", "catch_x"], false]]


import json
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    GetRateError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, Any] | None]


def parse_mkeventd_status(string_table: StringTable) -> Section:
    parsed: dict[str, Mapping[str, Any] | None] = {}
    site: str | None = None
    for line in string_table:
        try:
            data = json.loads(line[0])
        except ValueError:
            # The agent plug-in asks the event console for json OutputFormat, but
            # older versions always provide python format - even when other format
            # was requested. Skipping the site. Won't eval data from other systems.
            continue

        if len(data) == 1:
            site = data[0]
            parsed[site] = None  # Site is marked as down until overwritten later
        elif site:
            # strip "status_" from the column names
            keys = [col[7:] for col in data[0]]
            parsed[site] = dict(zip(keys, data[1]))

    return parsed


def discover_mkeventd_status(section: Section) -> DiscoveryResult:
    for site, status in section.items():
        if status is not None:
            yield Service(item=site)


def check_mkeventd_status(item: str, section: Section) -> CheckResult:
    if item not in section:
        return

    status = section[item]

    # Ignore down sites. This happens on a regular basis due to restarts
    # of the core. The availability of a site is monitored with 'omd_status'.
    if status is None:
        yield Result(state=State.OK, summary="Currently not running")
        return

    yield Result(state=State.OK, summary=f"Current events: {status['num_open_events']}")
    yield Metric("num_open_events", status["num_open_events"])

    yield Result(
        state=State.OK,
        summary=f"Virtual memory: {render.bytes(status['virtual_memory_size'])}",
    )
    yield Metric("process_virtual_size", status["virtual_memory_size"])

    # Event limits
    if status["event_limit_active_overall"]:
        yield Result(state=State.CRIT, summary="Overall event limit active")
    else:
        yield Result(state=State.OK, summary="Overall event limit inactive")

    for ty in ["hosts", "rules"]:
        limited = status[f"event_limit_active_{ty}"]
        if limited:
            yield Result(
                state=State.WARN,
                summary=f"Event limit active for {len(limited)} {ty} ({', '.join(limited)})",
            )
        else:
            yield Result(state=State.OK, summary=f"No {ty} event limit active")

    # Rates
    columns = [
        ("Received messages", "message"),
        ("Rule hits", "rule_hit"),
        ("Rule tries", "rule_trie"),
        ("Message drops", "drop"),
        ("Created events", "event"),
        ("Client connects", "connect"),
    ]
    rates = {}
    this_time = time.time()
    for title, col in columns:
        try:
            rate = get_rate(
                get_value_store(), col, this_time, status[col + "s"], raise_overflow=True
            )
        except GetRateError:
            continue
        rates[col] = rate
        yield Result(state=State.OK, summary=f"{title}: {rate:.2f}/s")
        yield Metric(f"average_{col}_rate", rate)

    # Hit rate
    if rates.get("rule_trie", 0.0) == 0.0:
        hit_rate_txt = "-"
    else:
        hit_ratio = rates["rule_hit"] / rates["rule_trie"] * 100
        hit_rate_txt = f"{hit_ratio:.2f}%"
        yield Metric("average_rule_hit_ratio", hit_ratio)
    yield Result(state=State.OK, summary=f"Rule hit ratio: {hit_rate_txt}")

    # Time columns
    time_columns = [
        ("Processing time per message", "processing"),
        ("Time per client request", "request"),
        ("Replication synchronization", "sync"),
    ]
    for title, name in time_columns:
        time_value = status.get(f"average_{name}_time")
        if time_value:
            txt = f"{time_value * 1000:.2f} ms"
            yield Metric(f"average_{name}_time", time_value)
        else:
            if name == "sync":
                continue  # skip if not available
            txt = "-"
        yield Result(state=State.OK, summary=f"{title}: {txt}")


agent_section_mkeventd_status = AgentSection(
    name="mkeventd_status",
    parse_function=parse_mkeventd_status,
)


check_plugin_mkeventd_status = CheckPlugin(
    name="mkeventd_status",
    service_name="OMD %s Event Console",
    discovery_function=discover_mkeventd_status,
    check_function=check_mkeventd_status,
)
