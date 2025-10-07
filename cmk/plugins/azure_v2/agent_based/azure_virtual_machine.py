#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterator, Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.azure_v2.agent_based.lib import (
    create_check_metrics_function_single,
    create_discover_by_metrics_function,
    create_discover_by_metrics_function_single,
    get_service_labels_from_resource_tags,
    iter_resource_attributes,
    MetricData,
    parse_resource,
    Resource,
)
from cmk.plugins.lib import interfaces

_MAP_STATES = {
    # Provisioning states
    "succeeded": 0,
    "updating": 1,
    "failed": 2,
    # Power states listed here:
    # https://docs.microsoft.com/en-us/azure/virtual-machines/windows/tutorial-manage-vm
    "starting": 0,
    "running": 0,
    "stopping": 1,
    "stopped": 1,  # VMs in the stopped state still incur compute charges.
    "deallocating": 0,
    "deallocated": 0,  # VMs in the Deallocated state do not incur compute charges.
    "unknown": 3,
}

_PROVISIONING_STATES = {"succeeded", "updating", "failed"}
_POWER_STATES = set(_MAP_STATES) - _PROVISIONING_STATES


class VMStatus(NamedTuple):
    name: str
    value: str
    message: str


VMSummaryParams = Mapping[str, Mapping[str, tuple[float, float]]]


agent_section_azure_virtualmachines = AgentSection(
    name="azure_v2_virtualmachines",
    parse_function=parse_resource,
)


#   .--VM------------------------------------------------------------------.
#   |                          __     ____  __                             |
#   |                          \ \   / /  \/  |                            |
#   |                           \ \ / /| |\/| |                            |
#   |                            \ V / | |  | |                            |
#   |                             \_/  |_|  |_|                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_azure_virtual_machine(section: Resource) -> DiscoveryResult:
    yield Service(labels=get_service_labels_from_resource_tags(section.tags))


def get_statuses(resource: Resource) -> Iterator[tuple[str, VMStatus]]:
    for status in resource.specific_info.get("statuses", []):
        if (code := status.get("code")) is None:
            continue

        status_name, status_value = code.split("/")[:2]
        parsed_status_value = status_value.lower() if status_value != "-" else "unknown"
        message = status.get("message")
        parsed_message = f" ({message})" if message else ""

        yield status_name, VMStatus(status_name, parsed_status_value, parsed_message)


def check_azure_virtual_machine(params: Mapping[str, int], section: Resource) -> CheckResult:
    statuses = dict(get_statuses(section))

    map_provisioning_states = {k: v for k, v in params.items() if k in _PROVISIONING_STATES}
    map_power_states = {k: v for k, v in params.items() if k in _POWER_STATES}

    for status_name, mapping, summary_template in (
        ("ProvisioningState", map_provisioning_states, "Provisioning"),
        ("PowerState", map_power_states, "VM"),
    ):
        if (status := statuses.get(status_name)) is None:
            yield Result(
                state=State(mapping.get("unknown", State.WARN)),
                summary=f"{summary_template} unknown",
            )
            continue

        yield Result(
            state=State(mapping.get(status.value, State.WARN)),
            summary=f"{summary_template} {status.value}{status.message}",
        )

    for key, value in iter_resource_attributes(section):
        yield Result(state=State.OK, summary=f"{key}: {value}")


check_plugin_azure_virtual_machine = CheckPlugin(
    name="azure_v2_virtual_machine",
    sections=["azure_v2_virtualmachines"],
    service_name="Azure/VM",
    discovery_function=discover_azure_virtual_machine,
    check_function=check_azure_virtual_machine,
    check_ruleset_name="azure_v2_vms",
    check_default_parameters=_MAP_STATES,
)


def discover_azure_vm_cpu_utilization(section: Resource) -> DiscoveryResult:
    yield from create_discover_by_metrics_function_single("average_Percentage_CPU")(section)


def check_azure_vm_cpu_utilization(
    params: Mapping[str, tuple[float, float]], section: Resource
) -> CheckResult:
    yield from create_check_metrics_function_single(
        [
            MetricData(
                "average_Percentage_CPU",
                "util",
                "CPU utilization",
                render.percent,
                upper_levels_param="levels",
            )
        ]
    )(params, section)


check_plugin_azure_vm_cpu_utilization = CheckPlugin(
    name="azure_v2_vm_cpu_utilization",
    sections=["azure_v2_virtualmachines"],
    service_name="Azure/VM CPU utilization",
    discovery_function=discover_azure_vm_cpu_utilization,
    check_function=check_azure_vm_cpu_utilization,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"levels": (65.0, 90.0)},
)


#   .--CPU Credits---------------------------------------------------------.
#   |          ____ ____  _   _    ____              _ _ _                 |
#   |         / ___|  _ \| | | |  / ___|_ __ ___  __| (_) |_ ___           |
#   |        | |   | |_) | | | | | |   | '__/ _ \/ _` | | __/ __|          |
#   |        | |___|  __/| |_| | | |___| | |  __/ (_| | | |_\__ \          |
#   |         \____|_|    \___/   \____|_|  \___|\__,_|_|\__|___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_azure_vm_burst_cpu_credits(
    params: Mapping[str, tuple[float, float]], section: Resource
) -> CheckResult:
    yield from create_check_metrics_function_single(
        [
            MetricData(
                "average_CPU_Credits_Consumed",
                "cpu_credits_consumed",
                "Consumed",
                str,
            ),
            MetricData(
                "average_CPU_Credits_Remaining",
                "cpu_credits_remaining",
                "Remaining",
                str,
                lower_levels_param="levels",
            ),
        ]
    )(params, section)


check_plugin_azure_vm_burst_cpu_credits = CheckPlugin(
    name="azure_v2_vm_burst_cpu_credits",
    sections=["azure_v2_virtualmachines"],
    service_name="Azure/VM Burst CPU Credits",
    discovery_function=create_discover_by_metrics_function_single(
        "average_CPU_Credits_Consumed",
        "average_CPU_Credits_Remaining",
    ),
    check_function=check_azure_vm_burst_cpu_credits,
    check_ruleset_name="azure_v2_vm_burst_cpu_credits",
    check_default_parameters={},
)


#   .--Memory--------------------------------------------------------------.
#   |               __  __                                                 |
#   |              |  \/  | ___ _ __ ___   ___  _ __ _   _                 |
#   |              | |\/| |/ _ \ '_ ` _ \ / _ \| '__| | | |                |
#   |              | |  | |  __/ | | | | | (_) | |  | |_| |                |
#   |              |_|  |_|\___|_| |_| |_|\___/|_|   \__, |                |
#   |                                                |___/                 |
#   '----------------------------------------------------------------------'


def check_azure_vm_memory(
    params: Mapping[str, tuple[float, float]], section: Resource
) -> CheckResult:
    yield from create_check_metrics_function_single(
        [
            MetricData(
                "average_Available_Memory_Bytes",
                "mem_available",
                "Available memory",
                render.bytes,
                lower_levels_param="levels",
            ),
        ]
    )(params, section)


check_plugin_azure_vm_memory = CheckPlugin(
    name="azure_v2_vm_memory",
    sections=["azure_v2_virtualmachines"],
    service_name="Azure/VM Memory",
    discovery_function=create_discover_by_metrics_function_single("average_Available_Memory_Bytes"),
    check_function=check_azure_vm_memory,
    check_ruleset_name="memory_available",
    check_default_parameters={},
)


#   .--Disk----------------------------------------------------------------.
#   |                          ____  _     _                               |
#   |                         |  _ \(_)___| | __                           |
#   |                         | | | | / __| |/ /                           |
#   |                         | |_| | \__ \   <                            |
#   |                         |____/|_|___/_|\_\                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_azure_vm_disk(
    params: Mapping[str, tuple[float, float]], section: Resource
) -> CheckResult:
    if (read_bytes := section.metrics.get("total_Disk_Read_Bytes")) is not None:
        yield from check_levels_v1(
            read_bytes.value / 60,
            levels_upper=params.get("disk_read"),
            metric_name="disk_read_throughput",
            label="Read",
            render_func=render.iobandwidth,
        )

    if (write_bytes := section.metrics.get("total_Disk_Write_Bytes")) is not None:
        yield from check_levels_v1(
            write_bytes.value / 60,
            levels_upper=params.get("disk_write"),
            metric_name="disk_write_throughput",
            label="Write",
            render_func=render.iobandwidth,
        )

    if (read_ops := section.metrics.get("average_Disk_Read_Operations/Sec")) is not None:
        yield from check_levels_v1(
            read_ops.value,
            levels_upper=params.get("disk_read_ios"),
            metric_name="disk_read_ios",
            label="Read operations",
            render_func=lambda x: f"{x:.2f}/s",
        )

    if (write_ops := section.metrics.get("average_Disk_Write_Operations/Sec")) is not None:
        yield from check_levels_v1(
            write_ops.value,
            levels_upper=params.get("disk_write_ios"),
            metric_name="disk_write_ios",
            label="Write operations",
            render_func=lambda x: f"{x:.2f}/s",
        )


check_plugin_azure_vm_disk = CheckPlugin(
    name="azure_v2_vm_disk",
    sections=["azure_v2_virtualmachines"],
    service_name="Azure/VM Disk",
    discovery_function=create_discover_by_metrics_function_single(
        "total_Disk_Read_Bytes",
        "total_Disk_Write_Bytes",
        "average_Disk_Read_Operations/Sec",
        "average_Disk_Write_Operations/Sec",
    ),
    check_function=check_azure_vm_disk,
    check_ruleset_name="azure_v2_vm_disk",
    check_default_parameters={},
)


#   .--Network IO----------------------------------------------------------.
#   |          _   _      _                      _      ___ ___            |
#   |         | \ | | ___| |___      _____  _ __| | __ |_ _/ _ \           |
#   |         |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ /  | | | | |          |
#   |         | |\  |  __/ |_ \ V  V / (_) | |  |   <   | | |_| |          |
#   |         |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\ |___\___/           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_azure_vm_network_io(section: Resource) -> DiscoveryResult:
    yield from create_discover_by_metrics_function(
        "total_Network_In_Total", "total_Network_Out_Total"
    )({"Network IO": section})


def check_azure_vm_network_io(
    item: str, params: Mapping[str, Any], section: Resource
) -> CheckResult:
    in_octets = None
    if (In_Total := section.metrics.get("total_Network_In_Total")) is not None:
        in_octets = In_Total.value / 60
    out_octets = None
    if (Out_Total := section.metrics.get("total_Network_Out_Total")) is not None:
        out_octets = Out_Total.value / 60
    interface = interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
        interfaces.InterfaceWithRates(
            attributes=interfaces.Attributes(
                index="0",
                descr=item,
                alias=item,
                type="1",
                oper_status="1",
            ),
            rates=interfaces.Rates(in_octets=in_octets, out_octets=out_octets),
            get_rate_errors=[],
        ),
        timestamp=time.time(),
        value_store=get_value_store(),
        params=params,
    )
    yield from interfaces.check_single_interface(item, params, interface)


check_plugin_azure_vm_network_io = CheckPlugin(
    name="azure_v2_vm_network_io",
    sections=["azure_v2_virtualmachines"],
    service_name="Azure/VM %s",
    discovery_function=discover_azure_vm_network_io,
    check_function=check_azure_vm_network_io,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
)
