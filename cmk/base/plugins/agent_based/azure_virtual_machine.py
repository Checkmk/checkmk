#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import NamedTuple

from .agent_based_api.v1 import check_levels, IgnoreResultsError, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.azure import iter_resource_attributes, parse_resources, Resource, Section

_MAP_PROVISIONING = {
    "succeeded": 0,
    "failed": 2,
}

_MAP_POWER = {
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


class VMStatus(NamedTuple):
    name: str
    value: str
    message: str


VMSummaryParams = Mapping[str, Mapping[str, tuple[float, float]]]


register.agent_section(
    name="azure_virtualmachines",
    parse_function=parse_resources,
)


def discover_azure_virtual_machine(section: Section) -> DiscoveryResult:
    for item in section.keys():
        yield Service(item=item)


def get_statuses(resource: Resource) -> Iterator[tuple[str, VMStatus]]:
    for status in resource.specific_info.get("statuses", []):
        if (code := status.get("code")) is None:
            continue

        status_name, status_value = code.split("/")[:2]
        parsed_status_value = status_value.lower() if status_value != "-" else "unknown"
        message = status.get("message")
        parsed_message = f" ({message})" if message else ""

        yield status_name, VMStatus(status_name, parsed_status_value, parsed_message)


def check_azure_virtual_machine(
    item: str, params: Mapping[str, Mapping[str, int]], section: Section
) -> CheckResult:
    if (resource := section.get(item)) is None:
        raise IgnoreResultsError("Data not present at the moment")

    statuses = dict(get_statuses(resource))

    map_provisioning_states = params.get("map_provisioning_states", {})
    map_power_states = params.get("map_power_states", {})

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

    for key, value in iter_resource_attributes(resource):
        yield Result(state=State.OK, summary=f"{key}: {value}")


register.check_plugin(
    name="azure_virtual_machine",
    sections=["azure_virtualmachines"],
    service_name="VM %s",
    discovery_function=discover_azure_virtual_machine,
    check_function=check_azure_virtual_machine,
    check_ruleset_name="azure_vms",
    check_default_parameters={
        "map_provisioning_states": _MAP_PROVISIONING,
        "map_power_states": _MAP_POWER,
    },
)


def discover_azure_virtual_machine_summary(section: Section) -> DiscoveryResult:
    if len(section) > 1:
        yield Service()


def check_state(state: str, count: int, levels: VMSummaryParams) -> tuple[State, str]:
    for result in check_levels(
        value=count,
        levels_upper=levels.get(state, {}).get("levels"),
        levels_lower=levels.get(state, {}).get("levels_lower"),
        render_func=lambda x: str(int(x)),
    ):
        if result.state != State.OK:
            summary = f"{count} {state} {result.summary.split(maxsplit=1)[1]}"
            return result.state, summary

        if count:
            return State.OK, f"{count} {state}"

    return State.OK, ""


def get_status_result(
    name: str, occurred_states: list[str], all_states: set[str], levels: VMSummaryParams
) -> CheckResult:
    state_results = [check_state(s, occurred_states.count(s), levels) for s in sorted(all_states)]

    state = State.worst(*(s[0] for s in state_results))
    summary = " / ".join(s[1] for s in state_results if s[1])
    yield Result(state=state, summary=f"{name}: {summary}")


def check_azure_virtual_machine_summary(
    params: Mapping[str, VMSummaryParams], section: Section
) -> CheckResult:

    resources = section.values()
    all_statuses = [dict(get_statuses(r)) for r in resources]

    provisionings = [
        s["ProvisioningState"].value if "ProvisioningState" in s else "unknown"
        for s in all_statuses
    ]
    provisioning_levels = params.get("levels_provisioning", {})
    provisioning_states = set(provisionings + list(_MAP_PROVISIONING))

    yield from get_status_result(
        "Provisioning", provisionings, provisioning_states, provisioning_levels
    )

    powers = [s["PowerState"].value if "PowerState" in s else "unknown" for s in all_statuses]
    power_levels = params.get("levels_power", {})
    power_states = set(powers + list(_MAP_POWER))

    yield from get_status_result("Power states", powers, power_states, power_levels)

    names = (r.name for r in resources)
    for name, provisioning, power in sorted(zip(names, provisionings, powers)):
        yield Result(state=State.OK, notice=f"{name}: Provisioning {provisioning}, VM {power}")


register.check_plugin(
    name="azure_virtual_machine_summary",
    sections=["azure_virtualmachines"],
    service_name="VM Summary",
    discovery_function=discover_azure_virtual_machine_summary,
    check_function=check_azure_virtual_machine_summary,
    check_ruleset_name="azure_vms_summary",
    check_default_parameters={
        "levels_provisioning": {
            "failed": {"levels": (1, 1)},
        },
        "levels_power": {
            "unknown": {"levels": (1, 2)},
        },
    },
)
