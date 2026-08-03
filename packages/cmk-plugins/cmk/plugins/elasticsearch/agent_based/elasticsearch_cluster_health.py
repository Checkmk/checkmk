#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# <<<elasticsearch_cluster_health>>>
# status green
# number_of_nodes 5
# unassigned_shards 0
# number_of_pending_tasks 0
# number_of_in_flight_fetch 0
# timed_out False
# active_primary_shards 0
# task_max_waiting_in_queue_millis 0
# cluster_name My-cluster
# relocating_shards 0
# active_shards_percent_as_number 100.0
# active_shards 0
# initializing_shards 0
# number_of_data_nodes 5
# delayed_unassigned_shards 0


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer untile we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
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

cluster_info = {
    "status": "Status",
    "cluster_name": "Name",
    "number_of_nodes": "Nodes",
    "number_of_data_nodes": "Data nodes",
}
shards_info = {
    "active_shards": "Active",
    "active_shards_percent_as_number": "Active in percent",
    "active_primary_shards": "Active primary",
    "unassigned_shards": "Unassigned",
    "initializing_shards": "Initializing",
    "relocating_shards": "Relocating",
    "delayed_unassigned_shards": "Delayed unassigned",
    "number_of_in_flight_fetch": "Ongoing shard info requests",
}
tasks_info = {
    "number_of_pending_tasks": "Pending tasks",
    "timed_out": "Timed out",
    "task_max_waiting_in_queue_millis": "Task max waiting",
}

default_cluster_state = {
    "green": 0,
    "yellow": 1,
    "red": 2,
}


def parse_elasticsearch_cluster_health(string_table: StringTable) -> dict[str, Any]:
    parsed: dict[str, Any] = {}

    for line in string_table:
        try:
            if any(s in line for s in cluster_info):
                inst = parsed.setdefault("Info", {})
                if line[0] == "status":
                    inst[line[0]] = line[1], default_cluster_state.get(line[1], 2)
                else:
                    inst[line[0]] = line[1], cluster_info[line[0]]
                continue

            if any(s in line for s in shards_info):
                inst = parsed.setdefault("Shards", {})
                inst[line[0]] = line[1], shards_info[line[0]]
                continue

            if any(s in line for s in tasks_info):
                inst = parsed.setdefault("Tasks", {})
                inst[line[0]] = line[1], tasks_info[line[0]]
                continue

        except (IndexError, ValueError):
            pass

    return parsed


def discover_elasticsearch_cluster_health(section: dict[str, Any]) -> DiscoveryResult:
    yield Service()


def check_elasticsearch_cluster_health(
    params: Mapping[str, Any], section: dict[str, Any]
) -> CheckResult:
    for info, values in sorted(section["Info"].items()):
        value = values[0]
        infotext = values[1]

        if info == "cluster_name":
            yield Result(state=State.OK, summary=f"{infotext}: {value}")
        elif info == "status":
            default_state = infotext
            infotext = "Status:"
            if value in params:
                yield Result(
                    state=State(params[value]),
                    summary=f"{infotext} {value} (State changed by rule)",
                )
            else:
                yield Result(state=State(default_state), summary=f"{infotext} {value}")
        else:
            warn, crit = params.get(info) or (None, None)
            yield from check_levels(
                int(value),
                info,
                (None, None, warn, crit),
                human_readable_func=int,
                infoname=infotext,
            )


agent_section_elasticsearch_cluster_health = AgentSection(
    name="elasticsearch_cluster_health",
    parse_function=parse_elasticsearch_cluster_health,
)


check_plugin_elasticsearch_cluster_health = CheckPlugin(
    name="elasticsearch_cluster_health",
    service_name="Elasticsearch Cluster Health",
    discovery_function=discover_elasticsearch_cluster_health,
    check_function=check_elasticsearch_cluster_health,
    check_ruleset_name="elasticsearch_cluster_health",
    check_default_parameters={},
)


def check_elasticsearch_cluster_health_shards(
    params: Mapping[str, Any], section: dict[str, Any]
) -> CheckResult:
    if (shards := section.get("Shards")) is None:
        return

    for shard, values in sorted(shards.items()):
        value = values[0]
        infotext = values[1]
        warn, crit = params.get(shard) or (None, None)

        if shard in {"active_primary_shards", "active_shards"}:
            yield from check_levels(
                int(value),
                shard,
                (None, None, warn, crit),
                human_readable_func=int,
                infoname=infotext,
            )
        elif shard == "active_shards_percent_as_number":
            yield from check_levels(
                float(value),
                shard,
                (None, None, warn, crit),
                human_readable_func=render.percent,
                infoname=infotext,
            )
        else:
            yield from check_levels(
                int(value),
                shard,
                (warn, crit, None, None),
                human_readable_func=int,
                infoname=infotext,
            )


check_plugin_elasticsearch_cluster_health_shards = CheckPlugin(
    name="elasticsearch_cluster_health_shards",
    service_name="Elasticsearch Cluster Shards",
    sections=["elasticsearch_cluster_health"],
    discovery_function=discover_elasticsearch_cluster_health,
    check_function=check_elasticsearch_cluster_health_shards,
    check_ruleset_name="elasticsearch_cluster_shards",
    check_default_parameters={"active_shards_percent_as_number": (100.0, 50.0)},
)


def check_elasticsearch_cluster_health_tasks(
    params: Mapping[str, Any], section: dict[str, Any]
) -> CheckResult:
    if (tasks := section.get("Tasks")) is None:
        return

    for task, values in sorted(tasks.items()):
        value = values[0]
        infotext = values[1]

        if task == "timed_out":
            state = State.OK if value == "False" else State.WARN
            yield Result(state=state, summary=f"{infotext}: {value}")
        else:
            value = int(value)
            warn, crit = params.get(task) or (None, None)
            yield from check_levels(value, task, (warn, crit, None, None), infoname=infotext)


check_plugin_elasticsearch_cluster_health_tasks = CheckPlugin(
    name="elasticsearch_cluster_health_tasks",
    service_name="Elasticsearch Cluster Tasks",
    sections=["elasticsearch_cluster_health"],
    discovery_function=discover_elasticsearch_cluster_health,
    check_function=check_elasticsearch_cluster_health_tasks,
    check_ruleset_name="elasticsearch_cluster_tasks",
    check_default_parameters={},
)
