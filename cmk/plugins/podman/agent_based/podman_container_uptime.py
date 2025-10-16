#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.lib import uptime

from .lib import SectionPodmanContainerInspect


def _is_active_container(status: str) -> bool:
    return status in ("running", "exited")


def calculate_uptime(now: datetime.datetime, started_at: str) -> uptime.Section:
    uptime_sec = (now - datetime.datetime.fromisoformat(started_at)).total_seconds()

    return uptime.Section(
        uptime_sec=uptime_sec,
        message=None,
    )


def discover_podman_container_uptime(
    section_podman_container_inspect: SectionPodmanContainerInspect | None,
    section_uptime: uptime.Section | None,
) -> DiscoveryResult:
    if section_uptime:
        for _service in uptime.discover(section_uptime):
            # if the uptime service of the checkmk agent is
            # present, we don't need this service.
            return
    if not section_podman_container_inspect:
        return

    if _is_active_container(section_podman_container_inspect.state.status):
        yield Service()


def check_podman_container_uptime(
    params: Mapping[str, Any],
    section_podman_container_inspect: SectionPodmanContainerInspect | None,
    section_uptime: uptime.Section | None,
) -> CheckResult:
    if not section_podman_container_inspect:
        return

    if section_podman_container_inspect.state.status != "running":
        yield Result(
            state=State.OK,
            summary=f"Operational state: {section_podman_container_inspect.state.status}",
        )
        return

    yield from uptime.check(
        params=params,
        section=calculate_uptime(
            datetime.datetime.now(tz=datetime.UTC),
            section_podman_container_inspect.state.started_at,
        ),
    )


check_plugin_podman_container_uptime = CheckPlugin(
    name="podman_container_uptime",
    service_name="Uptime",
    sections=["podman_container_inspect", "uptime"],
    discovery_function=discover_podman_container_uptime,
    check_function=check_podman_container_uptime,
    check_ruleset_name="uptime",
    check_default_parameters={},
)
