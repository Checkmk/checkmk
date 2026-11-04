#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable
from cmk.plugins.prism.lib import load_json, v4_power_state
from cmk.plugins.prism.v4_models import GuestTools, VmDetails, VmStatsSample

Section = Mapping[str, Any]


def parse_prism_vm(string_table: StringTable) -> Section:
    return load_json(string_table)


# The legacy stats keys and the v4 fields they come from
_LEGACY_STATS = {
    "controller_avg_io_latency_usecs": "controller_avg_io_latency_micros",
    "controller_avg_read_io_latency_usecs": "controller_avg_read_io_latency_micros",
    "controller_avg_write_io_latency_usecs": "controller_avg_write_io_latency_micros",
    "controller_avg_read_io_size_kbytes": "controller_avg_read_io_size_kb",
    "controller_avg_write_io_size_kbytes": "controller_avg_write_io_size_kb",
    "hypervisor_cpu_usage_ppm": "hypervisor_cpu_usage_ppm",
    "hypervisor.cpu_ready_time_ppm": "hypervisor_cpu_ready_time_ppm",
    "guest.memory_usage_ppm": "guest_memory_usage_ppm",
}


def _newest(samples: Sequence[VmStatsSample], field: str) -> int | None:
    values = [
        value
        for sample in sorted(samples, key=lambda sample: sample.timestamp)
        if (value := getattr(sample, field)) is not None
    ]
    return values[-1] if values else None


def _legacy_stats(vm: VmDetails, samples: Sequence[VmStatsSample]) -> dict[str, str]:
    # The legacy API sends the stats as text, and the stats plugins discover a service on any
    # non-empty text, "0" included. v4 leaves out stats it hasn't collected for a VM, where the
    # legacy API reports "-1"; writing "-1" keeps the services that legacy discovers for them.
    stats = {
        legacy: "-1" if (value := _newest(samples, field)) is None else str(value)
        for legacy, field in _LEGACY_STATS.items()
    }
    if vm.hypervisor == "ESXI":
        # ESXi VMs have no guest memory usage: no memory service
        del stats["guest.memory_usage_ppm"]
    # "-1" makes the memory check compute the usage from memoryCapacityInBytes
    stats["guest.memory_usage_bytes"] = "-1"
    return stats


def _legacy_guest_tools(tools: GuestTools | None) -> dict[str, object]:
    # The legacy API reports the tools of every VM, v4 only of VMs where they were set up
    if tools is None:
        return {"installedVersion": None, "enabled": False}
    return {
        "installedVersion": tools.version if tools.is_installed else None,
        "enabled": bool(tools.is_enabled),
    }


def parse_prism_vm_v2(string_table: StringTable) -> Section:
    if not string_table:
        return {}
    vm = VmDetails.model_validate_json(string_table[0][0])
    section: dict[str, object] = {
        "vmName": vm.name,
        "powerState": v4_power_state(vm.power_state),
        "hostName": vm.host_name,
        "memoryCapacityInBytes": vm.memory_size_bytes,
        "protectionDomainName": None,
        "nutanixGuestTools": _legacy_guest_tools(vm.guest_tools),
    }
    if vm.num_vcpus is not None:
        section["numVCpus"] = vm.num_vcpus
    if vm.protection_type is not None:
        section["protectionType"] = vm.protection_type
    # Without stats, the stats plugins report nothing for the VM
    if vm.stats is not None:
        section["stats"] = _legacy_stats(vm, vm.stats)
    return section


def host_label_prism_vm(section: Section) -> HostLabelGenerator:  # noqa: ARG001
    """Host label function

    Labels:
        cmk/nutanix/object:
            This label is set to either "control_plane" for the host with the special agent, "node"
            for Nutanix nodes or "vm" for VMs hosted in Nutanix.

    """
    yield HostLabel("cmk/nutanix/object", "vm")


agent_section_prism_vm = AgentSection(
    name="prism_vm",
    parse_function=parse_prism_vm,
    host_label_function=host_label_prism_vm,
)

agent_section_prism_vm_v2 = AgentSection(
    name="prism_vm_v2",
    parsed_section_name="prism_vm",
    parse_function=parse_prism_vm_v2,
    host_label_function=host_label_prism_vm,
)
