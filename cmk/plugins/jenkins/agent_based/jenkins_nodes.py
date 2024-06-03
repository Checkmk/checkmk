#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
)

from .lib import render_integer

_MAP_NODE_STATES: Final = {
    True: "yes",
    False: "no",
}


Section = Mapping[str, Sequence[Mapping]]


def parse_jenkins_nodes(string_table) -> Section:  # type: ignore[no-untyped-def]
    parsed: dict[str, list[Mapping]] = {}

    for line in string_table:
        node_detail = json.loads(line[0])

        for node in node_detail:
            try:
                parsed.setdefault(node["displayName"], []).append(node)
            except KeyError:
                pass

    return parsed


agent_section_jenkins_nodes = AgentSection(
    name="jenkins_nodes",
    parse_function=parse_jenkins_nodes,
)


def discover_jenkins_nodes(section: Section) -> DiscoveryResult:
    for item, values in section.items():
        for line in values:
            if (label_data := line.get("assignedLabels")) is None:
                continue

            service_labels = [
                ServiceLabel(f"cmk/jenkins_node_label_{label_name}", "yes")
                for label in label_data
                if (label_name := label.get("name")) is not None and label_name != item
            ]

        yield Service(item=item, parameters={}, labels=service_labels)


def _get_optional_value(
    mon_data: Mapping[str, Mapping[str, float | int] | None], key: str, *, value: str
) -> float | int | None:
    k = mon_data.get(key)
    if k is not None:
        return k.get(value)

    return None


def check_jenkins_nodes(  # pylint: disable=too-many-branches
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    item_data = section.get(item)
    if item_data is None:
        return

    for node in item_data:
        node_desc = node.get("description")
        if node_desc and node_desc is not None:
            yield Result(state=State.OK, summary=f"Description: {node_desc.strip().title()}")

        for key, infotext in [
            ("jnlpAgent", "Is JNLP agent"),
            ("idle", "Is idle"),
        ]:
            data = node.get(key)

            # description can be an empty string
            if data is not None and data != "":
                if key != "description":
                    data = _MAP_NODE_STATES[data]

                yield Result(state=State.OK, summary=f"{infotext}: {data}")

        exec_key = "numExecutors"
        if (exec_data := node.get(exec_key)) is not None:
            exec_name = "jenkins_%s" % exec_key.lower()

            yield from check_levels(
                exec_data,
                metric_name="jenkins_num_executors",
                levels_lower=params.get(exec_name),
                render_func=render_integer,
                label="Total number of executors",
            )

        for key, infotext in [
            ("busyExecutors", "Number of busy executors"),
            ("idleExecutors", "Number of idle executors"),
        ]:
            exec_label_data = node.get("assignedLabels")

            if exec_label_data is None:
                continue

            for executor in exec_label_data:
                # list of two dicts like [{"busyExecutors": 0,
                # "idleExecutors": 1}, {"busyExecutors": 0,
                # "idleExecutors": 1}], we only need one entry here
                executors = executor.get(key)
                break

            if executors is None:
                continue

            executor_name = "jenkins_%s" % key.lower()

            yield from check_levels(
                executors,
                metric_name="jenkins_%s_executors" % key[0:4],
                levels_upper=params.get(executor_name),
                render_func=render_integer,
                label=infotext,
            )

        # get labels for each node
        label_collection = [
            label_name
            for labels in (node.get("assignedLabels") or [])
            if (label_name := labels.get("name")) is not None and label_name != item
        ]

        mode = "Unknown"
        mode_state = State.UNKNOWN
        try:
            mode = node["assignedLabels"][0]["nodes"][0]["mode"]
            mode_state = State.OK
        except (KeyError, ValueError):
            pass

        mode_infotext = f"Mode: {mode.title()} "

        if mode == "EXCLUSIVE" and label_collection:
            mode_infotext += f"(Labels: {' '.join(label_collection)})"

        if (mode_expected := params.get("jenkins_mode")) is not None:
            if mode_expected != mode:
                mode_state = State.CRIT
                mode_infotext += f" (expected: {mode_expected.title()})"

        yield Result(state=mode_state, summary=mode_infotext)

        offline_state = node["offline"]
        state = State(params["jenkins_offline"]) if offline_state else State.OK

        yield Result(state=state, summary=f"Offline: {_MAP_NODE_STATES[offline_state]}")

        if not (mon_data := node.get("monitorData", {})):
            return

        if (
            response_time := _get_optional_value(
                mon_data, "hudson.node_monitors.ResponseTimeMonitor", value="average"
            )
        ) is not None:
            yield from check_levels(
                response_time / 1000.0,
                metric_name="avg_response_time",
                levels_upper=params.get("avg_response_time"),
                label="Average response time",
                render_func=render.timespan,
            )

        if (
            diff := _get_optional_value(mon_data, "hudson.node_monitors.ClockMonitor", value="diff")
        ) is not None:
            yield from check_levels(
                abs(diff) / 1000.0,
                metric_name="jenkins_clock",
                levels_upper=params.get("jenkins_clock"),
                label="Clock difference",
                render_func=render.timespan,
            )

        if (
            size := _get_optional_value(
                mon_data, "hudson.node_monitors.TemporarySpaceMonitor", value="size"
            )
        ) is not None:
            yield from check_levels(
                size,
                metric_name="jenkins_temp",
                levels_lower=params.get("jenkins_temp"),
                label="Free temp space",
                render_func=render.bytes,
            )


check_plugin_jenkins_nodes = CheckPlugin(
    name="jenkins_nodes",
    service_name="Jenkins Node %s",
    discovery_function=discover_jenkins_nodes,
    check_function=check_jenkins_nodes,
    check_default_parameters={"jenkins_offline": State.CRIT.value},
    check_ruleset_name="jenkins_nodes",
)
