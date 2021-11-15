#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Dict, Final, List, Mapping, Sequence, Tuple, Union

from .agent_based_api.v1 import check_levels, register, render, Result, Service, ServiceLabel, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

_MAP_NODE_STATES: Final = {
    True: "yes",
    False: "no",
}


Section = Mapping[str, Sequence[Mapping]]


def parse_jenkins_nodes(string_table) -> Section:
    parsed: Dict[str, List[Mapping]] = {}

    for line in string_table:
        node_detail = json.loads(line[0])

        for node in node_detail:
            try:
                parsed.setdefault(node["displayName"], []).append(node)
            except KeyError:
                pass

    return parsed


register.agent_section(
    name="jenkins_nodes",
    parse_function=parse_jenkins_nodes,
)


def discover_jenkins_nodes(section: Section) -> DiscoveryResult:
    for item, values in section.items():
        for line in values:
            label_data = line.get("assignedLabels")
            if label_data is None:
                continue

            service_labels = [
                ServiceLabel("cmk/jenkins_node_label_%s" % label_name, "yes")
                for label in label_data
                if (label_name := label.get("name")) is not None and label_name != item
            ]

        yield Service(item=item, parameters={}, labels=service_labels)


def check_jenkins_nodes(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    item_data = section.get(item)
    if item_data is None:
        return

    for node in item_data:

        node_desc = node.get("description")
        if node_desc and node_desc is not None:
            yield Result(state=State.OK, summary=f"Description: {node_desc.title()}")

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
        exec_data = node.get(exec_key)

        if exec_data is not None:
            exec_name = "jenkins_%s" % exec_key.lower()

            yield from check_levels(
                exec_data,
                metric_name="jenkins_num_executors",
                levels_lower=params.get(exec_name),
                render_func=lambda x: str(int(x)),
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
                render_func=lambda x: str(int(x)),
                label=infotext,
            )

        # get labels for each node
        labels_data = node.get("assignedLabels")
        label_collection = ""
        if labels_data is not None:
            for labels in labels_data:
                label_name = labels.get("name")
                if label_name is not None and label_name != item:
                    label_collection += " %s" % label_name

        mode = "Unknown"
        mode_state = State.UNKNOWN
        mode_infotext = "Mode: "
        try:
            mode = node["assignedLabels"][0]["nodes"][0]["mode"]
            mode_state = State.OK
        except (KeyError, ValueError):
            pass

        mode_infotext += "%s " % mode.title()

        if mode == "EXCLUSIVE" and label_collection:
            mode_infotext += "(Labels:%s)" % label_collection

        if params.get("jenkins_mode") is not None:
            mode_expected = params["jenkins_mode"]
            if mode_expected != mode:
                mode_state = State.CRIT
                mode_infotext += " (expected: %s)" % mode_expected.title()

        yield Result(state=mode_state, summary=mode_infotext)

        offline_state = node["offline"]
        state = State(params["jenkins_offline"]) if offline_state else State.OK

        yield Result(state=state, summary=f"Offline: {_MAP_NODE_STATES[offline_state]}")

        for key, column, value, info, ds_key, hr_func in [
            (
                "monitorData",
                "hudson.node_monitors.ResponseTimeMonitor",
                "average",
                "Average response time",
                "avg_response_time",
                render.timespan,
            ),
            (
                "monitorData",
                "hudson.node_monitors.ClockMonitor",
                "diff",
                "Clock difference",
                "jenkins_clock",
                render.timespan,
            ),
            (
                "monitorData",
                "hudson.node_monitors.TemporarySpaceMonitor",
                "size",
                "Free temp space",
                "jenkins_temp",
                render.bytes,
            ),
        ]:

            levels_upper, levels_lower = _get_levels(params.get(ds_key), lower=value == "size")

            try:
                node_data = node[key][column][value]
            except (AttributeError, KeyError, TypeError):
                continue

            if value in ["average", "diff"]:
                # ms to s
                node_data = node_data / 1000.0

            yield from check_levels(
                node_data,
                metric_name=ds_key,
                levels_upper=levels_upper,
                levels_lower=levels_lower,
                render_func=hr_func,
                label=info,
            )


_Levels = Union[None, Tuple[float, float]]


def _get_levels(levels: Union[None, Tuple[float, ...]], *, lower: bool) -> Tuple[_Levels, _Levels]:
    if levels is None:
        return None, None
    if lower:
        return None, (
            levels[0] * 1024 * 1024,
            levels[1] * 1024 * 1024,
        )
    # presumably we have only len 4 or 2, but be safe.
    return (levels[0], levels[1]), (levels[2], levels[3]) if len(levels) >= 4 else None


register.check_plugin(
    name="jenkins_nodes",
    service_name="Jenkins Node %s",
    discovery_function=discover_jenkins_nodes,
    check_function=check_jenkins_nodes,
    check_default_parameters={"jenkins_offline": 2},
    check_ruleset_name="jenkins_nodes",
)
