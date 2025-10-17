#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Version 2
# healthy if all nodes are reachable (at discovery)
# <<<pvecm_nodes>>>
# Node Sts Inc Joined Name
# 1 M 35960 2016-01-20 13:17:24 BAR-host002
# 2 M 36020 2016-01-20 13:30:18 FOO-host001
# 3 M 35960 2016-01-20 13:17:24 FOO-host003
# 4 M 35964 2016-01-20 13:17:24 FOO-host004
# 5 M 35764 2016-01-20 12:59:03 FOO-host002
# 6 M 36032 2016-01-20 13:34:27 BAR-host003
# 7 M 35960 2016-01-20 13:17:24 BAR-host001

# faulty because some nodes are missing
# <<<pvecm_nodes>>>
# Node Sts Inc Joined Name
# 1 M 35960 2016-01-20 13:17:24 BAR-host002
# 2 M 36020 2016-01-20 13:30:18 FOO-host001
# 4 M 35964 2016-01-20 13:17:24 FOO-host004
# 6 M 36032 2016-01-20 13:34:27 BAR-host003
# 7 M 35960 2016-01-20 13:17:24 BAR-host001

# faulty communication between nodes
# <<<pvecm_nodes>>>
# Node Sts Inc Joined Name
# 1 M 35960 2016-01-20 13:17:24 BAR-host002
# 2 M 36020 FOO-host001
# 3 M 35960 2016-01-20 13:17:24 FOO-host003
# 4 M 35964 2016-01-20 13:17:24 FOO-host004
# 5 M 35764 FOO-host002
# 6 M 36032 BAR-host003
# 7 M 35960 2016-01-20 13:17:24 BAR-host001

# Version >2
# <<<pvecm_nodes>>>
#
# Membership information
# ~~~~~~~~~~~~~~~~~~~~~~
#     Nodeid      Votes Name
#          1          1 hp1 (local)
#          2          1 hp2
#          3          1 hp3
#          4          1 hp4

# Version >2 with QDevcie
# <<<pvecm_nodes>>>
#
# Membership information
# ~~~~~~~~~~~~~~~~~~~~~~
#     Nodeid      Votes    Qdevice Name
#          1          1    A,V,NMW hp1 (local)
#          2          1    A,V,NMW hp2
#          0          1            QDevice
#


from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

type Section = Mapping[str, Mapping[str, str]]


def parse_pvecm_nodes(string_table: StringTable) -> Section:
    parsed = dict[str, Mapping[str, str]]()
    header = None
    parse_func = None
    for line in string_table:
        if line == ["Node", "Sts", "Inc", "Joined", "Name"]:
            header = ["node_id", "status", "joined", "name"]
            parse_func = _parse_version_eq_2
            continue

        if line == ["Nodeid", "Votes", "Name"]:
            header = ["node_id", "votes", "name"]
            parse_func = _parse_version_gt_2
            continue

        if line == ["Nodeid", "Votes", "Qdevice", "Name"]:
            header = ["node_id", "votes", "qdevice", "name"]
            parse_func = _parse_version_gt_2_with_qdevice
            continue

        if header is None or parse_func is None:
            continue

        k, v = parse_func(line, header)
        parsed.setdefault(k, v)
    return parsed


def _parse_version_eq_2(
    line: Sequence[str], header: Sequence[str]
) -> tuple[str, Mapping[str, str]]:
    if len(line) == 6:
        data = dict(zip(header[:3], [*line[:2], " ".join(line[3:5])]))
    else:
        data = dict(zip(["node_id", "status"], line[:2]))
    return line[-1], data


def _parse_version_gt_2(
    line: Sequence[str], header: Sequence[str]
) -> tuple[str, Mapping[str, str]]:
    return " ".join(line[2:]), dict(zip(header[:2], line[:2]))


def _parse_version_gt_2_with_qdevice(
    line: Sequence[str], header: Sequence[str]
) -> tuple[str, Mapping[str, str]]:
    if len(line) > 3:
        name = " ".join(line[3:])
    else:
        name = line[2]  # QDevice
    return name, dict(zip(header[:3], line[:3]))


def inventory_pvecm_nodes(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_pvecm_nodes(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        # sure? general policy would be to go to unknown.
        yield Result(state=State.CRIT, summary="Node is missing")
        return

    map_states = {
        "m": (State.OK, "member of the cluster"),
        "x": (State.WARN, "not a member of the cluster"),
        "d": (State.CRIT, "known to the cluster but disallowed access to it"),
    }

    yield Result(state=State.OK, summary=f"ID: {data['node_id']}")

    if "status" in data:
        state, state_readable = map_states[data["status"].lower()]
        yield Result(state=state, summary=f"Status: {state_readable}")
    if "joined" in data:
        yield Result(state=State.OK, summary=f"Joined: {data['joined']}")
    if "votes" in data:
        yield Result(state=State.OK, summary=f"Votes: {data['votes']}")


agent_section_pvecm_nodes = AgentSection(
    name="pvecm_nodes",
    parse_function=parse_pvecm_nodes,
)


check_plugin_pvecm_nodes = CheckPlugin(
    name="pvecm_nodes",
    service_name="PVE Node %s",
    discovery_function=inventory_pvecm_nodes,
    check_function=check_pvecm_nodes,
)
