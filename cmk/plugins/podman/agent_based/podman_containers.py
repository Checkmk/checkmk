#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, Field

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

DEFAULT_PARAMS: Params = {
    "dead": {"levels_upper": ("fixed", (1, 1))},
    "exited_as_non_zero": {"levels_upper": ("fixed", (1, 1))},
}


class Container(BaseModel, frozen=True):
    Id: str
    State: str
    ExitCode: int
    status: str = Field(alias="Status")
    creation: str = Field(alias="Created")
    name: Sequence[str] = Field(alias="Names")
    image: str = Field(alias="Image")
    labels: Mapping[str, str] | None = Field(alias="Labels")


class ContainerStateCounts(BaseModel, frozen=True):
    total: int
    running: int
    created: int
    paused: int
    stopped: int
    restarting: int
    removing: int
    dead: int
    exited: int
    exited_as_non_zero: int


class SectionContainers(BaseModel, frozen=True):
    containers: Sequence[Container]
    counts: ContainerStateCounts


def parse_podman_containers(string_table: StringTable) -> SectionContainers:
    all_containers = [
        Container.model_validate(container)
        for line in string_table
        if line
        for container in json.loads(line[0])
    ]
    counts = Counter(container.State.lower() for container in all_containers)
    exited_as_non_zero = sum(c.ExitCode != 0 for c in all_containers)

    return SectionContainers(
        containers=all_containers,
        counts=ContainerStateCounts(
            total=len(all_containers),
            running=counts["running"],
            created=counts["created"],
            paused=counts["paused"],
            stopped=counts["stopped"],
            restarting=counts["restarting"],
            removing=counts["removing"],
            dead=counts["dead"],
            exited=counts["exited"],
            exited_as_non_zero=exited_as_non_zero,
        ),
    )


agent_section_podman_containers: AgentSection = AgentSection(
    name="podman_containers", parse_function=parse_podman_containers
)


def discover_podman_containers(section: SectionContainers) -> DiscoveryResult:
    yield Service()


def check_podman_containers(params: Params, section: SectionContainers) -> CheckResult:
    if section.counts.total == 0:
        yield Result(
            state=State.OK,
            summary="No containers found",
        )
        return

    for container_state, count in section.counts.model_dump().items():
        state_params = params.get(container_state, {})
        yield from check_levels(
            value=count,
            metric_name=f"podman_containers_{container_state}_number",
            levels_lower=state_params.get("levels_lower"),
            levels_upper=state_params.get("levels_upper"),
            label=f"{container_state.capitalize().replace('_', ' ')}",
            render_func=lambda x: f"{int(x)}",
            notice_only=container_state in ("removing", "restarting", "exited_as_non_zero", "dead"),
            boundaries=(0, section.counts.total) if container_state == "running" else None,
        )


check_plugin_podman_containers = CheckPlugin(
    name="podman_containers",
    service_name="Podman containers",
    discovery_function=discover_podman_containers,
    check_function=check_podman_containers,
    check_ruleset_name="podman_containers",
    check_default_parameters=DEFAULT_PARAMS,
)
