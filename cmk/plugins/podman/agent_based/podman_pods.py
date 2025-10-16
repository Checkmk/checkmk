#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from collections import Counter
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    Result,
    Service,
    State,
    StringTable,
)

type Params = Mapping[
    str,
    Mapping[
        Literal["levels_lower", "levels_upper"],
        NoLevelsT | FixedLevelsT[int],
    ],
]

DEFAULT_PARAMS: Params = {"dead": {"levels_upper": ("fixed", (1, 1))}}


class Pod(BaseModel, frozen=True):
    Name: str
    Status: str


class PodsStateCounts(BaseModel, frozen=True):
    total: int
    running: int
    created: int
    stopped: int
    dead: int
    exited: int


def parse_podman_pods(string_table: StringTable) -> PodsStateCounts:
    pods = [Pod.model_validate(pod) for row in string_table if row for pod in json.loads(row[0])]
    counts = Counter(pod.Status.lower() for pod in pods)
    return PodsStateCounts(
        total=len(pods),
        running=counts["running"],
        created=counts["created"],
        stopped=counts["stopped"],
        dead=counts["dead"],
        exited=counts["exited"],
    )


agent_section_podman_pods: AgentSection = AgentSection(
    name="podman_pods", parse_function=parse_podman_pods
)


def discover_podman_pods(section: PodsStateCounts) -> DiscoveryResult:
    yield Service()


def check_podman_pods(params: Params, section: PodsStateCounts) -> CheckResult:
    if section.total == 0:
        yield Result(state=State.OK, summary="No pods found")
        return

    for pod_state, count in section.model_dump().items():
        state_params = params.get(pod_state, {})
        yield from check_levels(
            value=count,
            metric_name=f"podman_pods_{pod_state}_number",
            levels_lower=state_params.get("levels_lower"),
            levels_upper=state_params.get("levels_upper"),
            label=f"{pod_state.capitalize()}",
            render_func=lambda x: f"{int(x)}",
        )


check_plugin_podman_pods = CheckPlugin(
    name="podman_pods",
    service_name="Podman pods",
    discovery_function=discover_podman_pods,
    check_function=check_podman_pods,
    check_ruleset_name="podman_pods",
    check_default_parameters=DEFAULT_PARAMS,
)
