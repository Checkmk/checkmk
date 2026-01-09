#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # TODO: replace this by 'from cmk.agent_based.v2 import check_levels'.
    # This might require you to migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
)
from cmk.plugins.docker.lib import NodeInfoSection


def discover_docker_node_info(section: NodeInfoSection) -> DiscoveryResult:
    if section:
        yield Service()


def check_docker_node_info(section: NodeInfoSection) -> CheckResult:
    if "Name" in section:
        yield Result(state=State.OK, summary=f"Daemon running on host {section['Name']}")
    for state, key in [(State.CRIT, "Critical"), (State.UNKNOWN, "Unknown")]:
        for msg in section.get(key, ()):
            yield Result(state=state, summary=msg)


check_plugin_docker_node_info = CheckPlugin(
    name="docker_node_info",
    service_name="Docker node info",
    discovery_function=discover_docker_node_info,
    check_function=check_docker_node_info,
)


def check_docker_node_containers(
    params: Mapping[str, Any], section: NodeInfoSection
) -> CheckResult:
    if list(section.keys()) == ["Unknown"]:
        # The section error is reported by the "Docker node info" service
        raise IgnoreResultsError("Container statistics missing")

    for title, key, levels_prefix in (
        ("containers", "Containers", ""),
        ("running", "ContainersRunning", "running_"),
        ("paused", "ContainersPaused", "paused_"),
        ("stopped", "ContainersStopped", "stopped_"),
    ):
        count = section.get(key)
        if count is None:
            yield Result(
                state=State.UNKNOWN, summary=f"{title.title()}: count not present in agent output"
            )
            continue

        levels = params.get(f"{levels_prefix}upper_levels", (None, None))
        levels_lower = params.get(f"{levels_prefix}lower_levels", (None, None))
        yield from check_levels(
            count,
            title,
            levels + levels_lower,
            human_readable_func=lambda x: f"{x:d}",
            infoname=title.title(),
        )


check_plugin_docker_node_info_containers = CheckPlugin(
    name="docker_node_info_containers",
    service_name="Docker containers",
    sections=["docker_node_info"],
    discovery_function=discover_docker_node_info,
    check_function=check_docker_node_containers,
    check_ruleset_name="docker_node_containers",
    check_default_parameters={},
)
