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
    healthy: Literal[0, 1, 2, 3]
    starting: Literal[0, 1, 2, 3]
    unhealthy: Literal[0, 1, 2, 3]
    no_healthcheck: Literal[0, 1, 2, 3]


def discover_podman_container_health(
    section: SectionPodmanContainerInspect,
) -> DiscoveryResult:
    yield Service()


def check_podman_container_health(
    params: Params,
    section: SectionPodmanContainerInspect,
) -> CheckResult:
    details = f"""Last health report: {section.state.health.log[-1].output if section.state.health.log else "No health report available"}
    Health check command: {" ".join(section.config.healthcheck.command[1:]) if section.config.healthcheck else "No health check command configured"}
    Consecutive failed healthchecks: {section.state.health.failing_streak}
    On failure action: {section.config.healthcheck_on_failure_action}
    Last saved exit code: {section.state.health.log[-1].exit_code if section.state.health.log else "N/A"}"""

    health_status: Literal["no_healthcheck", "starting", "healthy", "unhealthy"] = (
        "no_healthcheck"
        if not section.config.healthcheck or not section.state.health.status
        else section.state.health.status
    )

    yield Result(
        state=State(params[health_status]),
        summary=f"Status: {section.state.health.status}"
        if section.config.healthcheck
        else "No health check configured",
        details=details,
    )


check_plugin_podman_container_health = CheckPlugin(
    name="podman_container_health",
    service_name="Health",
    sections=["podman_container_inspect"],
    discovery_function=discover_podman_container_health,
    check_function=check_podman_container_health,
    check_ruleset_name="podman_container_health",
    check_default_parameters=Params(
        healthy=0,
        starting=0,
        unhealthy=2,
        no_healthcheck=1,
    ),
)
