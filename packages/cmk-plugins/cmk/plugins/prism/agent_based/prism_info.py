#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# mypy: disable-error-code="explicit-any"

import re
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.prism.lib import load_json
from cmk.plugins.prism.v4_models import (
    ClusterConfig,
    ClusterStats,
    ClusterWithStats,
    newest,
)

Section = Mapping[str, Mapping[str, Any]]


def parse_prism_info(string_table: StringTable) -> Section:
    return load_json(string_table)


def host_label_prism_info(section: Section) -> HostLabelGenerator:  # noqa: ARG001
    """Host label function

    Labels:
        cmk/nutanix/object:
            This label is set to "control_plane" for the host with the special agent and, with the
            v4 API, for the host of each Nutanix cluster. It is set to "node" for Nutanix nodes and
            to "vm" for VMs hosted in Nutanix.

    """
    yield HostLabel("cmk/nutanix/object", "control_plane")


agent_section_prism_info = AgentSection(
    name="prism_info",
    parse_function=parse_prism_info,
    host_label_function=host_label_prism_info,
)


# The release within e.g. el8.5-release-ganges-7.5.0.6-stable-909c09d4325a
_RELEASE = re.compile(r"-(\d+(?:\.\d+)+)-")


def _version(config: ClusterConfig) -> str | None:
    """The full release like the legacy API: the build version has no patch level, and the
    legacy API shows the release of Prism Central as e.g. pc.7.5.1.1"""
    build_info = config.build_info
    if build_info.full_version and (release := _RELEASE.search(build_info.full_version)):
        version: str | None = release.group(1)
    else:
        version = build_info.version
    return f"pc.{version}" if version and config.is_prism_central else version


def _stats_v2(stats: ClusterStats) -> dict[str, str]:
    # Strings like the legacy API, so a value of 0 is reported as well
    return {
        legacy_key: str(value)
        for legacy_key, samples in (
            ("hypervisor_cpu_usage_ppm", stats.hypervisor_cpu_usage_ppm),
            ("hypervisor_memory_usage_ppm", stats.aggregate_hypervisor_memory_usage_ppm),
            ("controller_io_bandwidth_kBps", stats.io_bandwidth_kbps),
            ("controller_num_iops", stats.controller_num_iops),
            ("controller_avg_io_latency_usecs", stats.controller_avg_io_latency_usecs),
        )
        if (value := newest(samples)) is not None
    }


def parse_prism_info_v2(string_table: StringTable) -> Section:
    cluster = ClusterWithStats.model_validate_json(string_table[0][0])
    parsed: dict[str, Any] = {
        "name": cluster.name,
        "version": _version(cluster.config),
        "num_nodes": cluster.nodes.number_of_nodes,
        "stats": _stats_v2(cluster.stats or ClusterStats()),
    }
    return {key: value for key, value in parsed.items() if value is not None}


agent_section_prism_info_v2 = AgentSection(
    name="prism_info_v2",
    parsed_section_name="prism_info",
    parse_function=parse_prism_info_v2,
    # The host of each cluster takes over from the host of its Prism Element, so it is labelled
    # like the Prism Central host
    host_label_function=host_label_prism_info,
)


def discovery_prism_info(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_prism_info(section: Section) -> CheckResult:
    if section:
        summary = (
            f"Name: {section.get('name')}, "
            f"Version: {section.get('version')}, "
            f"Nodes: {section.get('num_nodes')}"
        )

        yield Result(
            state=State.OK,
            summary=summary,
        )


check_plugin_prism_info = CheckPlugin(
    name="prism_info",
    service_name="NTNX Cluster",
    sections=["prism_info"],
    discovery_function=discovery_prism_info,
    check_function=check_prism_info,
)
