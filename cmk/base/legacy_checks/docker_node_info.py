#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.docker import NodeInfoSection


def discover_docker_node_info(section: NodeInfoSection) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_docker_node_info(_no_item, _no_params, parsed):
    if "Name" in parsed:
        yield 0, "Daemon running on host %s" % parsed["Name"]
    for state, key in enumerate(("Warning", "Critical", "Unknown"), 1):
        if key in parsed:
            yield state, parsed[key]


check_info["docker_node_info"] = LegacyCheckDefinition(
    service_name="Docker node info",
    discovery_function=discover_docker_node_info,
    check_function=check_docker_node_info,
)


def check_docker_node_containers(_no_item, params, parsed):
    for title, key, levels_prefix in (
        ("containers", "Containers", ""),
        ("running", "ContainersRunning", "running_"),
        ("paused", "ContainersPaused", "paused_"),
        ("stopped", "ContainersStopped", "stopped_"),
    ):
        count = parsed.get(key)
        if count is None:
            yield 3, "%s: count not present in agent output" % title.title()
            continue

        levels = params.get("%supper_levels" % levels_prefix, (None, None))
        levels_lower = params.get("%slower_levels" % levels_prefix, (None, None))
        yield check_levels(
            count,
            title,
            levels + levels_lower,
            human_readable_func=lambda x: "%d" % x,
            infoname=title.title(),
        )


check_info["docker_node_info.containers"] = LegacyCheckDefinition(
    service_name="Docker containers",
    sections=["docker_node_info"],
    discovery_function=discover_docker_node_info,
    check_function=check_docker_node_containers,
    check_ruleset_name="docker_node_containers",
)
