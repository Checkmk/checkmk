#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal, TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

from .lib import SectionPodmanContainerInspect


class Params(TypedDict):
    created: Literal[0, 1, 2, 3]
    running: Literal[0, 1, 2, 3]
    paused: Literal[0, 1, 2, 3]
    restarting: Literal[0, 1, 2, 3]
    removing: Literal[0, 1, 2, 3]
    exited_with_zero: Literal[0, 1, 2, 3]
    exited_with_non_zero: Literal[0, 1, 2, 3]
    dead: Literal[0, 1, 2, 3]


DEFAULT_CHECK_PARAMETERS = Params(
    created=2,
    running=0,
    paused=2,
    restarting=2,
    removing=2,
    exited_with_zero=0,
    exited_with_non_zero=2,
    dead=2,
)


def discover_podman_container_status(
    section: SectionPodmanContainerInspect,
) -> DiscoveryResult:
    yield Service()


def check_podman_container_status(
    params: Params,
    section: SectionPodmanContainerInspect,
) -> CheckResult:
    status = (
        "exited_with_zero"
        if section.state.status == "exited" and section.state.exit_code == 0
        else "exited_with_non_zero"
        if section.state.status == "exited"
        else section.state.status
    )
    yield Result(
        state=State(params.get(status, 3)),
        summary=f"{status.capitalize().replace('_', ' ')}",
    )

    if section.pod:
        yield Result(state=State.OK, summary=f"Pod: {section.pod}")


check_plugin_podman_container_status = CheckPlugin(
    name="podman_container_status",
    service_name="Status",
    sections=["podman_container_inspect"],
    discovery_function=discover_podman_container_status,
    check_function=check_podman_container_status,
    check_ruleset_name="podman_container_status",
    check_default_parameters=DEFAULT_CHECK_PARAMETERS,
)
