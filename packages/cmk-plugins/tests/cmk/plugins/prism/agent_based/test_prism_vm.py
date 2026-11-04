#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import StringTable
from cmk.plugins.prism.agent_based.prism_vm import parse_prism_vm_v2

# vm-006 as the v4 agent writes it, recorded on a Prism Central 7.5 lab
RUNNING_VM = {
    "extId": "a725d6c8-92eb-4cb3-4ffe-02cba4f8848a",
    "name": "vm-006",
    "hypervisor": "AHV",
    "powerState": "ON",
    "hostName": "host-2",
    "numVcpus": 4,
    "memorySizeBytes": 8589934592,
    "protectionType": "UNPROTECTED",
    "guestTools": {"version": "4.5", "isInstalled": True, "isEnabled": True},
    "stats": [
        {
            "timestamp": "2026-11-04T15:00:00Z",
            "controllerAvgIoLatencyMicros": 1784,
            "controllerAvgReadIoLatencyMicros": 0,
            "controllerAvgWriteIoLatencyMicros": 1784,
            "controllerAvgReadIoSizeKb": 0,
            "controllerAvgWriteIoSizeKb": 12,
            "hypervisorCpuUsagePpm": 1254,
            "hypervisorCpuReadyTimePpm": 3,
            "guestMemoryUsagePpm": 879062,
        }
    ],
}

# vm-018 as the v4 agent writes it: off, so Prism Central has no I/O stats and no CPU ready time
VM_THAT_IS_OFF = {
    "extId": "1e187b3a-2c9b-4e9e-5433-42f12adbc654",
    "name": "vm-018",
    "hypervisor": "AHV",
    "powerState": "OFF",
    "numVcpus": 18,
    "memorySizeBytes": 34359738368,
    "protectionType": "UNPROTECTED",
    "stats": [
        {"timestamp": "2026-11-04T15:00:00Z", "guestMemoryUsagePpm": 0, "hypervisorCpuUsagePpm": 0}
    ],
}


def _section(vm: dict[str, object]) -> StringTable:
    return [[json.dumps(vm)]]


def test_running_vm_has_the_fields_of_the_legacy_section() -> None:
    # The legacy agent reported the same values for this VM at the same time
    assert parse_prism_vm_v2(_section(RUNNING_VM)) == {
        "vmName": "vm-006",
        "powerState": "on",
        "hostName": "host-2",
        "numVCpus": 4,
        "memoryCapacityInBytes": 8589934592,
        "protectionDomainName": None,
        "protectionType": "UNPROTECTED",
        "nutanixGuestTools": {"installedVersion": "4.5", "enabled": True},
        "stats": {
            "controller_avg_io_latency_usecs": "1784",
            "controller_avg_read_io_latency_usecs": "0",
            "controller_avg_write_io_latency_usecs": "1784",
            "controller_avg_read_io_size_kbytes": "0",
            "controller_avg_write_io_size_kbytes": "12",
            "hypervisor_cpu_usage_ppm": "1254",
            "hypervisor.cpu_ready_time_ppm": "3",
            "guest.memory_usage_ppm": "879062",
            "guest.memory_usage_bytes": "-1",
        },
    }


def test_stats_prism_central_has_not_collected_are_minus_one_as_in_legacy() -> None:
    stats = parse_prism_vm_v2(_section(VM_THAT_IS_OFF))["stats"]

    assert (stats["controller_avg_io_latency_usecs"], stats["hypervisor.cpu_ready_time_ppm"]) == (
        "-1",
        "-1",
    )


def test_vm_without_guest_tools_has_them_not_installed_and_disabled_as_in_legacy() -> None:
    section = parse_prism_vm_v2(_section(VM_THAT_IS_OFF))

    assert section["nutanixGuestTools"] == {"installedVersion": None, "enabled": False}


def test_guest_tools_set_up_but_not_installed_have_no_version() -> None:
    vm = {**RUNNING_VM, "guestTools": {"isInstalled": False, "isEnabled": True}}

    section = parse_prism_vm_v2(_section(vm))

    assert section["nutanixGuestTools"] == {"installedVersion": None, "enabled": True}


def test_newest_sample_of_each_stat_counts() -> None:
    vm = {
        **RUNNING_VM,
        "stats": [
            {"timestamp": "2026-11-04T15:00:00Z", "hypervisorCpuUsagePpm": 2},
            {"timestamp": "2026-11-04T14:45:00Z", "hypervisorCpuUsagePpm": 1},
        ],
    }

    assert parse_prism_vm_v2(_section(vm))["stats"]["hypervisor_cpu_usage_ppm"] == "2"


def test_esxi_vm_has_no_guest_memory_usage() -> None:
    vm = {**RUNNING_VM, "hypervisor": "ESXI"}

    assert "guest.memory_usage_ppm" not in parse_prism_vm_v2(_section(vm))["stats"]


def test_vm_has_no_stats_if_prism_central_could_not_list_them() -> None:
    vm = {key: value for key, value in RUNNING_VM.items() if key != "stats"}

    assert "stats" not in parse_prism_vm_v2(_section(vm))
