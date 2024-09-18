#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import enum
from collections.abc import Sequence
from typing import Literal, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    StringTable,
)
from cmk.plugins.kube.schemata.section import CountableNode, NodeCount

OptionalLevels = Literal["no_levels"] | tuple[Literal["levels"], tuple[int, int]]


def _node_is_control_plane(control_plane_roles: Sequence[str], node: CountableNode) -> bool:
    """Checkmks definition of a control plane node.

    >>> _node_is_control_plane(["blue"], CountableNode(ready=False, roles=["blue", "red"]))
    True
    >>> _node_is_control_plane([], CountableNode(ready=True, roles=["blue", "red"]))
    False
    """
    return any(role in node.roles for role in control_plane_roles)


@dataclasses.dataclass
class ReadyCount:
    ready: int
    not_ready: int
    total: int

    @classmethod
    def node_count(
        cls, control_plane_roles: Sequence[str], section: NodeCount
    ) -> tuple["ReadyCount", "ReadyCount"]:
        w_nodes = [n for n in section.nodes if not _node_is_control_plane(control_plane_roles, n)]
        cp_nodes = [n for n in section.nodes if _node_is_control_plane(control_plane_roles, n)]
        return (
            ReadyCount(
                ready=(w_ready := sum(n.ready for n in w_nodes)),
                not_ready=len(w_nodes) - w_ready,
                total=len(w_nodes),
            ),
            ReadyCount(
                ready=(cp_ready := sum(n.ready for n in cp_nodes)),
                not_ready=len(cp_nodes) - cp_ready,
                total=len(cp_nodes),
            ),
        )


class NodeType(enum.StrEnum):
    worker = "worker"
    control_plane = "control_plane"

    def pretty(self) -> str:
        match self:
            case NodeType.worker:
                return "Worker"
            case NodeType.control_plane:
                return "Control plane"


class LevelName(enum.StrEnum):
    levels_lower = "levels_lower"
    levels_upper = "levels_upper"


class KubeNodeCountVSResult(TypedDict):
    control_plane_roles: Sequence[str]
    worker_levels_lower: OptionalLevels
    worker_levels_upper: OptionalLevels
    control_plane_levels_lower: OptionalLevels
    control_plane_levels_upper: OptionalLevels


def parse(string_table: StringTable) -> NodeCount:
    return NodeCount.model_validate_json(string_table[0][0])


def discovery(section: NodeCount) -> DiscoveryResult:
    yield Service()


def _get_levels(
    params: KubeNodeCountVSResult,
    name: NodeType,
    level_name: LevelName,
) -> None | tuple[int, int]:
    match name, level_name:
        case NodeType.worker, LevelName.levels_lower:
            level = params.get("worker_levels_lower", "no_levels")
        case NodeType.worker, LevelName.levels_upper:
            level = params.get("worker_levels_upper", "no_levels")
        case NodeType.control_plane, LevelName.levels_lower:
            level = params.get("control_plane_levels_lower", "no_levels")
        case NodeType.control_plane, LevelName.levels_upper:
            level = params.get("control_plane_levels_upper", "no_levels")
        case _:
            raise ValueError(f"Combination of {name} and {level_name} unknown.")
    return level[1] if level != "no_levels" else None


def _check_levels(
    ready_count: ReadyCount, name: NodeType, params: KubeNodeCountVSResult
) -> CheckResult:
    levels_upper = _get_levels(params, name, LevelName.levels_upper)
    levels_lower = _get_levels(params, name, LevelName.levels_lower)
    result, metric = check_levels_v1(
        ready_count.ready,
        metric_name=f"kube_node_count_{name}_ready",
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        render_func=lambda x: str(int(x)),
        boundaries=(0, None),
    )
    assert isinstance(result, Result)
    levels = result.summary.removeprefix(str(ready_count.ready))
    if ready_count.total != 0:
        summary = f"{name.pretty()} nodes {ready_count.ready}/{ready_count.total}{levels}"
    else:
        summary = f"No {name.pretty().lower()} nodes found{levels}"
    yield Result(state=result.state, summary=summary)
    yield metric
    yield Metric(f"kube_node_count_{name}_not_ready", ready_count.not_ready)
    yield Metric(f"kube_node_count_{name}_total", ready_count.total)


def check(params: KubeNodeCountVSResult, section: NodeCount) -> CheckResult:
    worker, control_plane = ReadyCount.node_count(params["control_plane_roles"], section)
    yield from _check_levels(worker, NodeType.worker, params)
    yield from _check_levels(control_plane, NodeType.control_plane, params)


agent_section_kube_node_count_v1 = AgentSection(
    name="kube_node_count_v1",
    parse_function=parse,
    parsed_section_name="kube_node_count",
)

check_default_parameters = KubeNodeCountVSResult(
    control_plane_roles=["master", "control_plane"],
    worker_levels_lower="no_levels",
    worker_levels_upper="no_levels",
    control_plane_levels_lower="no_levels",
    control_plane_levels_upper="no_levels",
)


check_plugin_kube_node_count = CheckPlugin(
    name="kube_node_count",
    service_name="Nodes",
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="kube_node_count",
    check_default_parameters=check_default_parameters,
)
