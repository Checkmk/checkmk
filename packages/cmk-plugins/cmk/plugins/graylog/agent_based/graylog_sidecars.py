#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.graylog.lib import handle_iso_utc_to_localtimestamp

Section = dict[str, dict[str, Any]]

# <<<graylog_sidecars>>>
# {"sort": "node_name", "pagination": {"count": 1, "per_page": 50, "total": 1,
# "page": 1}, "sidecars": [{"co  llectors": null, "node_name": "testserver",
# "assignments": [], "node_id": "31c3e8f9-a6b2-41d4-be78-f6273c3cb0e5", "n
# ode_details": {"metrics": {"disks_75": ["/snap/gnome-calculator/501
# (100%)", "/snap/core/7713 (100%)", "/snap/gnome-  calculator/406 (100%)",
# "/snap/gtk-common-themes/1313 (100%)", "/snap/core18/1192 (100%)",
# "/snap/spotify/35 (100%)"  , "/snap/gnome-characters/317 (100%)",
# "/snap/gnome-3-26-1604/90 (100%)", "/snap/gnome-3-28-1804/71 (100%)",
# "/snap/  gnome-3-26-1604/92 (100%)", "/snap/gtk-common-themes/1198 (100%)",
# "/snap/gnome-logs/73 (100%)", "/snap/gnome-logs/8  1 (100%)",
# "/snap/gnome-characters/296 (100%)", "/snap/gnome-3-28-1804/67 (100%)",
# "/snap/core18/1144 (100%)", "/sna  p/gnome-system-monitor/100 (100%)",
# "/snap/gnome-system-monitor/95 (100%)", "/snap/core/7396 (100%)",
# "/snap/spotify  /36 (100%)"], "load_1": 0.49, "cpu_idle": 95.0}, "ip":
# "10.3.2.62", "operating_system": "Linux", "status": {"status"  : 1,
# "message": "Received no ping signal from sidecar", "collectors": []},
# "log_file_list": null}, "active": false,   "sidecar_version": "1.0.2",
# "last_seen": "2019-10-10T09:56:29.303Z"}], "filters": null, "only_active":
# false, "query  ": "", "total": 1, "order": "asc"}


def parse_graylog_sidecars(string_table: StringTable) -> Section:
    parsed: Section = {}

    for line in string_table:
        sidecar_data = json.loads(line[0])

        sidecar_nodename = sidecar_data.get("node_name")
        if sidecar_nodename is None:
            continue

        parsed.setdefault(
            sidecar_nodename,
            {
                "active": sidecar_data.get("active"),
                "collectors": sidecar_data.get("node_details", {})
                .get("status", {})
                .get("collectors"),
                "collector_msg": sidecar_data.get("node_details", {})
                .get("status", {})
                .get("message"),
                "last_seen": sidecar_data.get("last_seen"),
                "status": sidecar_data.get("node_details", {}).get("status", {}).get("status"),
            },
        )

    return parsed


def discover_graylog_sidecars(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_graylog_sidecars(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (item_data := section.get(item)):
        return

    active_msg = item_data.get("active")
    if active_msg is not None:
        msg = str(active_msg).replace("True", "yes").replace("False", "no")
        active_state = State.OK if active_msg else State(params.get("active_state", 2))
        yield Result(state=active_state, summary=f"Active: {msg}")

    last_seen = item_data.get("last_seen")
    if last_seen is not None:
        local_timestamp = handle_iso_utc_to_localtimestamp(last_seen)
        age = time.time() - local_timestamp

        yield Result(state=State.OK, summary=f"Last seen: {render.datetime(local_timestamp)}")

        warn, crit = params.get("last_seen", (None, None))
        yield from check_levels_v1(
            value=age,
            levels_upper=(warn, crit),
            render_func=render.timespan,
            label="Before",
        )

    collector_state = _handle_collector_states(item_data.get("status", 3), params)
    collector_msg = item_data.get("collector_msg")
    if collector_msg is not None:
        msg = collector_msg.split("/")
        if len(msg) == 3:
            for num_collector in msg:
                count, status = num_collector.strip().split(" ")

                yield from check_levels_v1(
                    value=int(count),
                    metric_name=f"collectors_{status}",
                    levels_upper=params.get(f"{status}_upper", (None, None)),
                    levels_lower=params.get(f"{status}_lower", (None, None)),
                    render_func=lambda v: f"{int(v)}",
                    label=f"Collectors {status}",
                )
        else:
            yield Result(state=State(collector_state), summary=f"Collectors: {collector_msg}")

    collector_data = item_data.get("collectors")
    if collector_data is None:
        return

    long_output: list[tuple[int, str]] = []
    for collector in collector_data:
        long_output_str = ""

        collector_id = collector.get("collector_id")
        if collector_id is not None:
            long_output_str += f"ID: {collector_id}"

        msg_text = collector.get("message")
        if msg_text is not None:
            long_output_str += f", Message: {msg_text}"

        collector_state = _handle_collector_states(collector.get("status", 3), params)
        long_output.append((collector_state, long_output_str))

    if not long_output:
        return

    max_state = max(state for state, _infotext in long_output)
    yield Result(state=State(max_state), summary="see long output for more details")

    for state, line in long_output:
        yield Result(state=State(state), notice=line)


def _handle_collector_states(collector_state: int, params: Mapping[str, Any]) -> int:
    if collector_state == 0:
        return int(params.get("running", 0))
    # "Received no ping signal from sidecar"
    if collector_state == 1:
        return int(params.get("no_ping", 2))
    if collector_state == 2:
        return int(params.get("failing", 2))
    if collector_state == 3:
        return int(params.get("stopped", 2))
    return 3


agent_section_graylog_sidecars = AgentSection(
    name="graylog_sidecars",
    parse_function=parse_graylog_sidecars,
)


check_plugin_graylog_sidecars = CheckPlugin(
    name="graylog_sidecars",
    service_name="Graylog Sidecar %s",
    discovery_function=discover_graylog_sidecars,
    check_function=check_graylog_sidecars,
    check_ruleset_name="graylog_sidecars",
    check_default_parameters={
        "running_lower": (1, 0),
        "stopped_upper": (1, 1),
        "failing_upper": (1, 1),
    },
)
