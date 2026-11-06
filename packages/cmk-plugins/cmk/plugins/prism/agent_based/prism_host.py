#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from typing import Any

from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable
from cmk.plugins.prism.lib import load_json, tier_usage_stats
from cmk.plugins.prism.v4_models import HostStats, newest, Node, NodeDisk

Section = dict[str, Any]


def parse_prism_host(string_table: StringTable) -> Section:
    return load_json(string_table)


def host_label_prism_host(section: Section) -> HostLabelGenerator:  # noqa: ARG001
    """Host label function

    Labels:
        cmk/nutanix/object:
            This label is set to either "control_plane" for the host with the special agent, "node"
            for Nutanix nodes or "vm" for VMs hosted in Nutanix.

        cmk/os_name:
            This label is set to the name of the operating system as reported by the agent as "OSName"

        cmk/os_platform:
            This label is set to the platform as reported by the agent as "OSPlatform". In case
            "OSPlatform" is not set, the value of "AgentOS" is used.

    """
    yield HostLabel("cmk/nutanix/object", "node")
    yield HostLabel("cmk/os_platform", "nutanix")
    yield HostLabel("cmk/os_name", "Nutanix AHV")


agent_section_prism_host = AgentSection(
    name="prism_host",
    parse_function=parse_prism_host,
    host_label_function=host_label_prism_host,
)


def _legacy_value(value: int | None) -> str:
    """Text, like the legacy API, which also reports -1 for a stat it doesn't know: the
    discovery finds the service for any text"""
    return str(-1 if value is None else value)


def _stats_v2(stats: HostStats) -> dict[str, str]:
    legacy: dict[str, str] = {}
    for legacy_key, samples in (
        ("controller_avg_io_latency_usecs", stats.controller_avg_io_latency_usecs),
        ("controller_avg_read_io_latency_usecs", stats.controller_avg_read_io_latency_usecs),
        ("controller_avg_write_io_latency_usecs", stats.controller_avg_write_io_latency_usecs),
        ("hypervisor_cpu_usage_ppm", stats.hypervisor_cpu_usage_ppm),
        ("hypervisor_memory_usage_ppm", stats.aggregate_hypervisor_memory_usage_ppm),
    ):
        legacy[legacy_key] = _legacy_value(newest(samples))
    for legacy_key, bandwidth_samples, iops_samples in (
        (
            "controller_avg_read_io_size_kbytes",
            stats.controller_read_io_bandwidth_kbps,
            stats.controller_num_read_iops,
        ),
        (
            "controller_avg_write_io_size_kbytes",
            stats.controller_write_io_bandwidth_kbps,
            stats.controller_num_write_iops,
        ),
    ):
        bandwidth, iops = newest(bandwidth_samples), newest(iops_samples)
        if bandwidth is None or iops is None:
            legacy[legacy_key] = _legacy_value(None)
        else:
            legacy[legacy_key] = _legacy_value(bandwidth // iops if iops else 0)
    return legacy


def _usage_stats_v2(node: Node) -> dict[str, str]:
    legacy: dict[str, str] = {}
    for legacy_key, samples in (
        ("storage.capacity_bytes", node.stats.storage_capacity_bytes),
        ("storage.free_bytes", node.stats.free_physical_storage_bytes),
    ):
        legacy[legacy_key] = _legacy_value(newest(samples))
    return legacy | tier_usage_stats(
        [(disk.config.storage_tier, disk.stats) for disk in node.disks]
    )


def _disk_hardware_config_v2(disk: NodeDisk) -> dict[str, object] | None:
    """None, like the legacy API for an empty slot, if the check can't tell the mount state"""
    advance_config = disk.config.disk_advance_config
    if advance_config.is_mounted is None:
        return None
    return {
        "bad": bool(advance_config.is_unhealthy),
        "model": disk.config.model,
        "serial_number": disk.config.serial_number,
        "mounted": advance_config.is_mounted,
    }


def parse_prism_host_v2(string_table: StringTable) -> Section:
    if not string_table:
        return {}
    node = Node.model_validate_json(string_table[0][0])
    parsed: Section = {
        legacy_key: value
        for legacy_key, value in (
            ("num_cpu_sockets", node.config.number_of_cpu_sockets),
            ("num_cpu_cores", node.config.number_of_cpu_cores),
            ("num_cpu_threads", node.config.number_of_cpu_threads),
            ("memory_capacity_in_bytes", node.config.memory_size_bytes),
            ("cpu_capacity_in_hz", newest(node.stats.cpu_capacity_hz)),
        )
        if value is not None
    }
    parsed["stats"] = _stats_v2(node.stats)
    parsed["usage_stats"] = _usage_stats_v2(node)
    # The legacy API names the disks by slot, v4 by location
    parsed["disk_hardware_configs"] = {
        str(disk.config.location): _disk_hardware_config_v2(disk)
        for disk in node.disks
        if disk.config.location is not None
    }
    return parsed


agent_section_prism_host_v2 = AgentSection(
    name="prism_host_v2",
    parsed_section_name="prism_host",
    parse_function=parse_prism_host_v2,
    host_label_function=host_label_prism_host,
)
