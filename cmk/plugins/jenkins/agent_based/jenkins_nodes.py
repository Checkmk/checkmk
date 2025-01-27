#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence
from contextlib import suppress
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
    StringTable,
)

from .lib import render_integer

_MAP_NODE_STATES: Final = {
    True: "yes",
    False: "no",
}

CHECK_DEFAULT_PARAMETERS: Final = {
    "jenkins_offline": State.CRIT.value,
    "jenkins_numexecutors": ("no_levels", None),
    "jenkins_numexecutors_upper": ("no_levels", None),
    "jenkins_busyexecutors_lower": ("no_levels", None),
    "jenkins_busyexecutors": ("no_levels", None),
    "jenkins_idleexecutors_lower": ("no_levels", None),
    "jenkins_idleexecutors": ("no_levels", None),
    "jenkins_temp": ("no_levels", None),
    "jenkins_clock": ("no_levels", None),
    "avg_response_time": ("no_levels", None),
}

Section = Mapping[str, Sequence[Mapping]]


def parse_jenkins_nodes(string_table: StringTable) -> Section:
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


def check_jenkins_nodes(
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
                levels_lower=params[exec_name],
                levels_upper=params[exec_name + "_upper"],
                render_func=render_integer,
                label="Total number of executors",
            )

        mode = "Unknown"
        mode_state = State.UNKNOWN

        assigned_labels = node.get("assignedLabels") or []
        if assigned_labels:
            # Select the proper label to base our executor data on
            # We try to find a good label by looking for one that matches
            # the name of the currently processed node.
            # If no match is found we take the first label.
            for label in assigned_labels:
                if label.get("name") == item:
                    break
            else:
                label = assigned_labels[0]

            for key in ("busy", "idle"):
                if (value := label.get(f"{key}Executors")) is None:
                    continue

                yield from check_levels(
                    value,
                    metric_name=f"jenkins_{key}_executors",
                    levels_upper=params[f"jenkins_{key}executors"],
                    levels_lower=params[f"jenkins_{key}executors_lower"],
                    render_func=render_integer,
                    label=f"Number of {key} executors",
                )

            with suppress(KeyError, ValueError):
                mode = label["nodes"][0]["mode"]
                mode_state = State.OK

        mode_infotext = [f"Mode: {mode.title()}"]

        # get labels for each node
        label_collection = [
            label_name
            for labels in assigned_labels
            if (label_name := labels.get("name")) is not None and label_name != item
        ]

        if mode == "EXCLUSIVE" and label_collection:
            mode_infotext.append(f"(Labels: {' '.join(label_collection)})")

        if (mode_expected := params.get("jenkins_mode")) is not None:
            if mode_expected != mode:
                mode_state = State.CRIT
                mode_infotext.append(f"(expected: {mode_expected.title()})")

        yield Result(state=mode_state, summary=" ".join(mode_infotext))

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
                levels_upper=params["avg_response_time"],
                label="Average response time",
                render_func=render.timespan,
            )

        if (
            diff := _get_optional_value(mon_data, "hudson.node_monitors.ClockMonitor", value="diff")
        ) is not None:
            yield from check_levels(
                abs(diff) / 1000.0,
                metric_name="jenkins_clock",
                levels_upper=params["jenkins_clock"],
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
                levels_lower=params["jenkins_temp"],
                label="Free temp space",
                render_func=render.bytes,
            )


check_plugin_jenkins_nodes = CheckPlugin(
    name="jenkins_nodes",
    service_name="Jenkins Node %s",
    discovery_function=discover_jenkins_nodes,
    check_function=check_jenkins_nodes,
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="jenkins_nodes",
)
