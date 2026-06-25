#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import time
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
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.graylog.lib import handle_iso_utc_to_localtimestamp

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


@dataclass(frozen=True)
class Collector:
    collector_id: str | None
    message: str | None
    status: int | None


@dataclass(frozen=True)
class Sidecar:
    active: bool | None
    collectors: list[Collector] | None
    collector_msg: str | None
    last_seen: str | None
    status: int | None


Section = Mapping[str, Sidecar]


def _parse_collector(collector: object) -> Collector:
    match collector:
        case {
            "collector_id": str() | None as collector_id,
            "message": str() | None as message,
            "status": int() | None as status,
        }:
            return Collector(collector_id=collector_id, message=message, status=status)
        case _:
            return Collector(collector_id=None, message=None, status=None)


class SidecarsParams(TypedDict):
    active_state: int
    last_seen: LevelsT[float]
    running_lower: LevelsT[int]
    running_upper: LevelsT[int]
    stopped_lower: LevelsT[int]
    stopped_upper: LevelsT[int]
    failing_lower: LevelsT[int]
    failing_upper: LevelsT[int]
    running: int
    stopped: int
    failing: int
    no_ping: int


def parse_graylog_sidecars(string_table: StringTable) -> Section:
    parsed: dict[str, Sidecar] = {}

    for line in string_table:
        # A sidecar always carries node_name/active/last_seen; node_details (with
        # the collector status block) is only present for registered sidecars.
        match json.loads(line[0]):
            case {
                "node_name": str(node_name),
                "active": bool() | None as active,
                "last_seen": str() | None as last_seen,
                "node_details": {
                    "status": {
                        "status": int() | None as status,
                        "message": str() | None as collector_msg,
                        **status_rest,
                    }
                },
            }:
                match status_rest.get("collectors"):
                    case list() as collectors_raw:
                        collectors: list[Collector] | None = [
                            _parse_collector(collector) for collector in collectors_raw
                        ]
                    case _:
                        collectors = None
            case {
                "node_name": str(node_name),
                "active": bool() | None as active,
                "last_seen": str() | None as last_seen,
            }:
                status = None
                collector_msg = None
                collectors = None
            case _:
                continue

        parsed.setdefault(
            node_name,
            Sidecar(
                active=active,
                collectors=collectors,
                collector_msg=collector_msg,
                last_seen=last_seen,
                status=status,
            ),
        )

    return parsed


def discover_graylog_sidecars(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_graylog_sidecars(item: str, params: SidecarsParams, section: Section) -> CheckResult:
    if (item_data := section.get(item)) is None:
        return

    if item_data.active is not None:
        msg = "yes" if item_data.active else "no"
        active_state = State.OK if item_data.active else State(params["active_state"])
        yield Result(state=active_state, summary=f"Active: {msg}")

    if item_data.last_seen is not None:
        local_timestamp = handle_iso_utc_to_localtimestamp(item_data.last_seen)
        age = time.time() - local_timestamp

        yield Result(state=State.OK, summary=f"Last seen: {render.datetime(local_timestamp)}")

        yield from check_levels(
            value=age,
            levels_upper=params["last_seen"],
            render_func=render.timespan,
            label="Before",
        )

    levels_upper_by_status: Mapping[str, LevelsT[int]] = {
        "running": params["running_upper"],
        "stopped": params["stopped_upper"],
        "failing": params["failing_upper"],
    }
    levels_lower_by_status: Mapping[str, LevelsT[int]] = {
        "running": params["running_lower"],
        "stopped": params["stopped_lower"],
        "failing": params["failing_lower"],
    }

    collector_state = _handle_collector_states(item_data.status, params)
    if item_data.collector_msg is not None:
        msg_parts = item_data.collector_msg.split("/")
        if len(msg_parts) == 3:
            for num_collector in msg_parts:
                count, status = num_collector.strip().split(" ")

                yield from check_levels(
                    value=int(count),
                    metric_name=f"collectors_{status}",
                    levels_upper=levels_upper_by_status.get(status),
                    levels_lower=levels_lower_by_status.get(status),
                    render_func=lambda v: f"{int(v)}",
                    label=f"Collectors {status}",
                )
        else:
            yield Result(
                state=State(collector_state),
                summary=f"Collectors: {item_data.collector_msg}",
            )

    if item_data.collectors is None:
        return

    long_output: list[tuple[int, str]] = []
    for collector in item_data.collectors:
        long_output_str = ""

        if collector.collector_id is not None:
            long_output_str += f"ID: {collector.collector_id}"

        if collector.message is not None:
            long_output_str += f", Message: {collector.message}"

        long_output.append((_handle_collector_states(collector.status, params), long_output_str))

    if not long_output:
        return

    max_state = max(state for state, _infotext in long_output)
    yield Result(state=State(max_state), summary="see long output for more details")

    for state, line in long_output:
        yield Result(state=State(state), notice=line)


def _handle_collector_states(collector_state: int | None, params: SidecarsParams) -> int:
    if collector_state == 0:
        return params["running"]
    # "Received no ping signal from sidecar"
    if collector_state == 1:
        return params["no_ping"]
    if collector_state == 2:
        return params["failing"]
    if collector_state == 3:
        return params["stopped"]
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
        "active_state": 2,
        "last_seen": ("no_levels", None),
        "running_lower": ("fixed", (1, 0)),
        "running_upper": ("no_levels", None),
        "stopped_lower": ("no_levels", None),
        "stopped_upper": ("fixed", (1, 1)),
        "failing_lower": ("no_levels", None),
        "failing_upper": ("fixed", (1, 1)),
        "running": 0,
        "stopped": 2,
        "failing": 2,
        "no_ping": 2,
    },
)
