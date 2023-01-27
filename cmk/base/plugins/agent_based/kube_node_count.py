#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import enum
from typing import Literal, Tuple, TypedDict, Union

from .agent_based_api.v1 import check_levels, Metric, register, Result, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.kube import CountableNode, NodeCount

OptionalLevels = Union[Literal["no_levels"], Tuple[Literal["levels"], Tuple[int, int]]]


def _node_is_control_plane(node: CountableNode) -> bool:
    return "master" in node.roles or "control_plane" in node.roles


@dataclasses.dataclass
class ReadyCount:
    ready: int = 0
    not_ready: int = 0

    @property
    def total(self) -> int:
        return self.ready + self.not_ready

    @classmethod
    def node_count(cls, section: NodeCount) -> tuple["ReadyCount", "ReadyCount"]:
        worker = cls()
        control_plane = cls()
        for node in section.nodes:
            if _node_is_control_plane(node):
                if node.ready:
                    control_plane.ready += 1
                else:
                    control_plane.not_ready += 1
            else:
                if node.ready:
                    worker.ready += 1
                else:
                    worker.not_ready += 1
        return worker, control_plane


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
    worker_levels_lower: OptionalLevels
    worker_levels_upper: OptionalLevels
    control_plane_levels_lower: OptionalLevels
    control_plane_levels_upper: OptionalLevels


def parse(string_table: StringTable) -> NodeCount:
    return NodeCount.parse_raw(string_table[0][0])


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
    result, metric = check_levels(
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
    worker, control_plane = ReadyCount.node_count(section)
    yield from _check_levels(worker, NodeType.worker, params)
    yield from _check_levels(control_plane, NodeType.control_plane, params)


register.agent_section(
    name="kube_node_count_v1",
    parse_function=parse,
    parsed_section_name="kube_node_count",
)

check_default_parameters = KubeNodeCountVSResult(
    worker_levels_lower="no_levels",
    worker_levels_upper="no_levels",
    control_plane_levels_lower="no_levels",
    control_plane_levels_upper="no_levels",
)


register.check_plugin(
    name="kube_node_count",
    service_name="Nodes",
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="kube_node_count",
    check_default_parameters=check_default_parameters,
)
