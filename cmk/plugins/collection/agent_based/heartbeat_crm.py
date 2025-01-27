#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import calendar
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

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

# Example outputs from agent:
# <<<heartbeat_crm>>>
# ============
# Last updated: Thu Jul  1 07:48:19 2010
# Current DC: mwp (118cc1e7-bbf3-4550-b820-cac372885be1)
# 2 Nodes configured.
# 2 Resources configured.
# ============
# Node: smwp (2395453b-d647-48ff-a908-a7cd76062265): online
# Node: mwp (118cc1e7-bbf3-4550-b820-cac372885be1): online
# Full list of resources:
# Resource Group: group_slapmaster
#     resource_virtip1  (ocf::heartbeat:IPaddr):  Started mwp
#     resource_virtip2  (ocf::heartbeat:IPaddr):  Started mwp
#     resource_pingnodes  (ocf::heartbeat:pingd): Started mwp
#     resource_slapmaster (ocf::heartbeat:OpenLDAP):  Started mwp
# resource_slapslave  (ocf::heartbeat:OpenLDAP):  Started smwp


KNOWN_RESOURCES_HEADERS = {"full list of resources:"}
KNOWN_FAILED_RESOURCE_ACTION_HEADERS = {
    "failed actions:",
    "failed resource actions:",
    "failed fencing actions:",
}


@dataclass(frozen=True, kw_only=True)
class Cluster:
    last_updated: float | None
    dc: str | None
    num_nodes: int | None
    num_resources: int | None
    error: str | None


@dataclass(frozen=True, kw_only=True)
class Resources:
    resources: Mapping[str, Sequence[Sequence[str]]]
    failed_actions: Sequence[str]


@dataclass(frozen=True, kw_only=True)
class Section:
    cluster: Cluster
    resources: Resources


def _parse_for_error(first_line: str) -> str | None:
    if (
        first_line.lower().startswith(("critical", "error:"))
        or "connection to cluster failed" in first_line.lower()
    ):
        return first_line
    return None


def _title(title: str) -> str:
    """
    >>> _title("")
    ''
    >>> _title("Foo")
    'Foo'
    >>> _title("Foo:")
    'Foo'
    >>> _title("Foo: bar baz")
    'Foo'
    """
    return title.split(":", 1)[0]


def heartbeat_crm_parse_general(general_section: Sequence[Sequence[str]]) -> Cluster:
    if (error := _parse_for_error(" ".join(general_section[0]))) is not None:
        return Cluster(
            last_updated=None,
            dc=None,
            num_nodes=None,
            num_resources=None,
            error=error,
        )

    last_updated = None
    dc = None
    num_nodes = None
    num_resources = None
    for line in general_section:
        line_txt = " ".join(line)
        title = _title(line_txt)

        if title == "Last updated":
            last_updated = _parse_last_updated(line)
            continue

        if title == "Current DC":
            dc = line[2]
            continue

        if "nodes and" in line_txt and "resources configured" in line_txt:
            # Some versions put number of nodes and resources in one line
            num_nodes = int(line[0])
            num_resources = int(line[3])
            continue

        if "nodes configured" in line_txt.lower():
            num_nodes = int(line[0])
            continue

        if (
            "resources configured" in line_txt.lower()
            or "resource instances configured" in line_txt.lower()
        ):
            # outputs may vary:
            # pacemaker version < 2.0.3: 21 Resources configured.
            # pacemaker version = 2.0.3:  3 resource instances configured
            num_resources = int(line[0])

    return Cluster(
        last_updated=last_updated,
        dc=dc,
        num_nodes=num_nodes,
        num_resources=num_resources,
        error=None,
    )


def _parse_last_updated(line: Sequence[str]) -> int:
    """
    >>> _parse_last_updated(["Last", "updated:", "Tue", "Sep", "8", "10:36:12", "2020"])
    1599561372
    >>> _parse_last_updated(['Last', 'updated:', 'Tue', 'Sep', '22', '11:20:53', '2015', 'Last', 'change:', 'Thu', 'Sep', '17', '14:52:42', '2015', 'by', 'root', 'via', 'crm_resource', 'on', 'bl64lnx-priv'])
    1442920853
    >>> _parse_last_updated(['Last', 'updated:', 'Wed', 'Nov', '29', '08:29:27', '2023', 'on', 'hdenagapp269'])
    1701246567
    """
    if line.count("Last") > 1:
        # Sometimes, `Last updated` and `Last changed` are combined into a single line
        line = line[: line.index("Last", 1)]
    return calendar.timegm(
        time.strptime(
            " ".join(line[2:7]),
            "%a %b %d %H:%M:%S %Y",
        )
    )


def heartbeat_crm_parse_resources(
    resources_section: Iterable[Sequence[str]],
) -> Mapping[str, Sequence[Sequence[str]]]:
    resources: dict[str, list[Sequence[str]]] = {}
    resource = ""
    mode = "single"

    for parts in resources_section:
        line = " ".join(parts)

        if line.startswith("Resource Group:"):
            # Resource group
            resource = _title(parts[2])
            resources[resource] = []
            mode = "resourcegroup"
        elif line.startswith("Clone Set:"):
            # Clone set
            resource = _title(parts[2])
            resources[resource] = []
            mode = "masterslaveset" if "(promotable)" in parts[-1] else "cloneset"
        elif line.startswith("Master/Slave Set:"):
            # Master/Slave set
            resource = _title(parts[2])
            resources[resource] = []
            mode = "masterslaveset"
        elif line[0] == "_":
            # Resource group or set member
            if mode == "resourcegroup":
                resources[resource].append(parts[1:])
            elif mode == "cloneset":
                if parts[1] == "Started:":
                    # Resources are only used to check that the master does not switch nodes.
                    # Clone and Slave information is discarded in the check function.
                    resources[resource].append(
                        [resource, "Clone", "Started", ", ".join(parts[3:-1])]
                    )
            elif mode == "masterslaveset":
                if parts[1] == "Masters:":
                    resources[resource].append([resource, "Master", "Started", parts[3]])
                if parts[1] == "Slaves:":
                    resources[resource].append([resource, "Slave", "Started", parts[3]])
        else:
            # Single resource
            resources[parts[0]] = [parts]

    return resources


def heartbeat_crm_parse_failed_resource_actions(
    failed_resource_actions_section: Iterable[Sequence[str]],
) -> Sequence[str]:
    """Join lines on space and ignore punctuations/extra spaces.

    Examples:

        >>> heartbeat_crm_parse_failed_resource_actions((l for l in [["*", "1", "2"], ["_", "3"]]))
        ['1 2 3']

        >>> heartbeat_crm_parse_failed_resource_actions((l for l in [["*", "1", "2"], ["_", "3"], ["_", "4"], ["*", "1", "2"], ["_", "3"]]))
        ['1 2 3 4', '1 2 3']

        >>> heartbeat_crm_parse_failed_resource_actions((l for l in [["1", "2", "3"], ["1", "2", "3"], ["*", "1"], ["_", "2", "3"]]))
        ['1 2 3', '1 2 3', '1 2 3']

        >>> heartbeat_crm_parse_failed_resource_actions((l for l in [["1", "2",], [" ", "3"]]))
        ['1 2 3']

        >>> heartbeat_crm_parse_failed_resource_actions((l for l in []))
        []

    """
    joined = []
    line = ""
    for part_list in failed_resource_actions_section:
        part = " ".join(part_list)
        if part.startswith("*"):
            if line:
                joined.append(line)
            line = part[2:]
        elif part.startswith(("_ ", "  ")):
            line += part[1:]
        else:
            if line:
                joined.append(line)
            line = part

    if line:
        joined.append(line)
    return joined


def _sanitise_line(line: Sequence[str]) -> Sequence[str]:
    """Ensure consistency across different versions of pacemaker.

    - General information should not contain any leading punctuation
    - List elements are denoted with "_"

    Examples:

    >>> _sanitise_line(["a"])
    ['a']
    >>> _sanitise_line(["_*", "a"])
    ['a']
    >>> _sanitise_line(["_", "a"])
    ['_', 'a']
    >>> _sanitise_line(["_", "*", "a"])
    ['_', 'a']
    """
    leading_character = line[0]

    if leading_character == "_*":
        # lines are prefixed with _* in pacemaker versions >= 2, e.g.:
        # _* Current DC: ha02 (version 2.0.3-5.el8_2.1-4b1f869f0f)
        return line[1:]

    if leading_character != "_":
        return line

    if line[1] == "*":
        # list elements are prefixed with "_ *" (artibrary number of spaces)
        # in pacemaker versions >= 2, e.g.:
        # _  * qpid_lvm	(ocf::heartbeat:LVM-activate):	 Started cbgdevd01
        # the leading character to denote a list is changed to "_" for
        # consistency, and to recognise list elements during later parsing
        sanitised_line = list(line[2:])
        sanitised_line.insert(0, "_")
        return sanitised_line

    return line


def _partition_string_table(iter_string_table, next_section_headers=None):
    if not next_section_headers:
        yield from (l for l in iter_string_table)
        return

    while (line := next(iter_string_table, None)) is not None and " ".join(
        line
    ).lower() not in next_section_headers:
        yield _sanitise_line(line)


def parse_heartbeat_crm(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    iter_string_table = iter(string_table)
    general_section = _partition_string_table(
        iter_string_table, next_section_headers=KNOWN_RESOURCES_HEADERS
    )
    resources_section = _partition_string_table(
        iter_string_table, next_section_headers=KNOWN_FAILED_RESOURCE_ACTION_HEADERS
    )
    failed_resource_actions_section = _partition_string_table(iter_string_table)

    return Section(
        cluster=heartbeat_crm_parse_general(list(general_section)),
        resources=Resources(
            resources=heartbeat_crm_parse_resources(resources_section),
            failed_actions=heartbeat_crm_parse_failed_resource_actions(
                failed_resource_actions_section
            ),
        ),
    )


agent_section_heartbeat_crm = AgentSection(
    name="heartbeat_crm",
    parse_function=parse_heartbeat_crm,
)

#   .--CRM-----------------------------------------------------------------.
#   |                          ____ ____  __  __                           |
#   |                         / ___|  _ \|  \/  |                          |
#   |                        | |   | |_) | |\/| |                          |
#   |                        | |___|  _ <| |  | |                          |
#   |                         \____|_| \_\_|  |_|                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_heartbeat_crm(
    params: Mapping[str, bool],
    section: Section,
) -> DiscoveryResult:
    yield Service(
        parameters={
            "num_nodes": section.cluster.num_nodes,
            "num_resources": section.cluster.num_resources,
            **({"dc": section.cluster.dc} if params["naildown_dc"] else {}),
        }
    )


def check_heartbeat_crm(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _check_heartbeat_crm(params, section, time.time())


def _check_heartbeat_crm(
    params: Mapping[str, Any],
    section: Section,
    now: float,
) -> CheckResult:
    if section.cluster.error is not None:
        yield Result(state=State.CRIT, summary=section.cluster.error)
        return

    # Check the freshness of the crm_mon output and terminate with CRITICAL
    # when too old information are found
    if too_old_result := _check_last_cluster_update(
        last_update=section.cluster.last_updated,
        now=now,
        max_age=params["max_age"],
    ):
        yield too_old_result
        return

    # Check for correct DC when enabled
    if (p_dc := params.get("dc")) is None or section.cluster.dc == p_dc:
        yield Result(state=State.OK, summary=f"DC: {section.cluster.dc}")
    else:
        yield Result(state=State.CRIT, summary=f"DC: {section.cluster.dc} (Expected {p_dc})")

    # Check for number of nodes when enabled
    if params["num_nodes"] is not None and section.cluster.num_nodes is not None:
        if section.cluster.num_nodes == params["num_nodes"]:
            yield Result(state=State.OK, summary="Nodes: %d" % (section.cluster.num_nodes,))
        else:
            yield Result(
                state=State.CRIT,
                summary="Nodes: %d (Expected %d)"
                % (section.cluster.num_nodes, params["num_nodes"]),
            )

    # Check for number of resources when enabled
    if params["num_resources"] is not None and section.cluster.num_resources is not None:
        if section.cluster.num_resources == params["num_resources"]:
            yield Result(state=State.OK, summary="Resources: %d" % (section.cluster.num_resources,))
        else:
            yield Result(
                state=State.CRIT,
                summary="Resources: %d (Expected %d)"
                % (section.cluster.num_resources, params["num_resources"]),
            )

    if not params.get("show_failed_actions"):
        return

    for action in section.resources.failed_actions:
        yield Result(state=State.WARN, summary=f"Failed: {action}")


def _check_last_cluster_update(
    *,
    last_update: float | None,
    now: float,
    max_age: float,
) -> Result | None:
    if last_update is None:
        return None
    if (delta := now - last_update) > max_age:
        return Result(
            state=State.CRIT,
            summary=f"Ignoring reported data (Status output too old: {render.timespan(delta)})",
        )
    return None


check_plugin_heartbeat_crm = CheckPlugin(
    name="heartbeat_crm",
    service_name="Heartbeat CRM General",
    discovery_function=discover_heartbeat_crm,
    discovery_ruleset_name="inventory_heartbeat_crm_rules",
    discovery_default_parameters={
        "naildown_dc": False,
        "naildown_resources": False,
    },
    check_function=check_heartbeat_crm,
    check_ruleset_name="heartbeat_crm",
    check_default_parameters={
        "max_age": 60,
    },
)

# .
#   .--Resources-----------------------------------------------------------.
#   |            ____                                                      |
#   |           |  _ \ ___  ___  ___  _   _ _ __ ___ ___  ___              |
#   |           | |_) / _ \/ __|/ _ \| | | | '__/ __/ _ \/ __|             |
#   |           |  _ <  __/\__ \ (_) | |_| | | | (_|  __/\__ \             |
#   |           |_| \_\___||___/\___/ \__,_|_|  \___\___||___/             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_heartbeat_crm_resources(
    params: Mapping[str, bool],
    section: Section,
) -> DiscoveryResult:
    # Full list of resources:
    # Resource Group: group_slapmaster
    #     resource_virtip1  (ocf::heartbeat:IPaddr):  Started mwp
    #     resource_virtip2  (ocf::heartbeat:IPaddr):  Started mwp
    #     resource_pingnodes  (ocf::heartbeat:pingd): Started mwp
    #     resource_slapmaster (ocf::heartbeat:OpenLDAP):  Started mwp
    # resource_slapslave  (ocf::heartbeat:OpenLDAP):  Started smwp
    for name, resources in section.resources.resources.items():
        # In naildown mode only resources which are started somewhere can be
        # inventorized
        if params.get("naildown_resources", False) and resources[0][2] != "Stopped":
            yield Service(item=name, parameters={"expected_node": resources[0][3]})
        else:
            yield Service(item=name)


class HeartbeatCrmResourcesParameters(TypedDict):
    expected_node: str | None
    monitoring_state_if_unmanaged_nodes: Literal[0, 1, 2, 3]


def check_heartbeat_crm_resources(
    item: str,
    params: HeartbeatCrmResourcesParameters,
    section: Section,
) -> CheckResult:
    if (resources := section.resources.resources.get(item)) is None:
        return

    yield from _check_heartbeat_crm_resources(resources, params)


def _check_heartbeat_crm_resources(
    resources: Sequence[Sequence[str]],
    params: HeartbeatCrmResourcesParameters,
) -> CheckResult:
    if not resources:
        yield Result(state=State.OK, summary="No resources found")

    unmanaged_nodes = set()

    for resource in resources:
        yield Result(state=State.OK, summary=" ".join(resource))

        if len(resource) in {3, 4} and resource[2] != "Started":
            yield Result(state=State.CRIT, summary=f'Resource is in state "{resource[2]}"')
            continue

        current_node = resource[3]
        if (
            (target_node := params["expected_node"])
            and target_node != current_node
            and resource[1] not in {"Slave", "Clone"}
        ):
            yield Result(state=State.CRIT, summary=f"Expected node: {target_node}")
        if "(unmanaged)" in resource:
            unmanaged_nodes.add(current_node)

    if unmanaged_nodes:
        yield Result(
            state=State(params["monitoring_state_if_unmanaged_nodes"]),
            summary=f"Unmanaged nodes: {', '.join(sorted(unmanaged_nodes))}",
        )


check_plugin_heartbeat_crm_resources = CheckPlugin(
    name="heartbeat_crm_resources",
    service_name="Heartbeat CRM %s",
    sections=["heartbeat_crm"],
    discovery_function=discover_heartbeat_crm_resources,
    discovery_ruleset_name="inventory_heartbeat_crm_rules",
    discovery_default_parameters={
        "naildown_dc": False,
        "naildown_resources": False,
    },
    check_function=check_heartbeat_crm_resources,
    check_ruleset_name="heartbeat_crm_resources",
    check_default_parameters=HeartbeatCrmResourcesParameters(
        expected_node=None,
        monitoring_state_if_unmanaged_nodes=1,
    ),
)
