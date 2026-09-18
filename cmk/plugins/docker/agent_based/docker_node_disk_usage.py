#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Service,
    StringTable,
)
from cmk.plugins.docker import lib as docker


def parse_docker_node_disk_usage(string_table: StringTable) -> Mapping[str, Mapping[str, Any]]:
    disk_usage = docker.parse_multiline(string_table).data
    return {item_type: r for r in disk_usage if (item_type := r.get("type")) is not None}


agent_section_docker_node_disk_usage = AgentSection(
    name="docker_node_disk_usage",
    parse_function=parse_docker_node_disk_usage,
)


def discover_docker_node_disk_usage(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_docker_node_disk_usage(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    if not section:
        # The section error is reported by the "Docker node info" service
        raise IgnoreResultsError("Disk usage missing")

    if not (data := section.get(item)):
        return
    for key, render_func in (
        ("size", render.bytes),
        ("reclaimable", render.bytes),
        ("count", lambda x: str(int(x))),
        ("active", lambda x: str(int(x))),
    ):
        yield from check_levels(
            data[key],
            levels_upper=params.get(key),
            metric_name=key,
            render_func=render_func,
            label=key.title(),
        )


check_plugin_docker_node_disk_usage = CheckPlugin(
    name="docker_node_disk_usage",
    service_name="Docker disk usage - %s",
    discovery_function=discover_docker_node_disk_usage,
    check_function=check_docker_node_disk_usage,
    check_ruleset_name="docker_node_disk_usage",
    check_default_parameters={},
)
