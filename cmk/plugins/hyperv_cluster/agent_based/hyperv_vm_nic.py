#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Thanks to Andreas Döhler for the contribution.

from collections.abc import Callable, Mapping
from typing import Final, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, str]]
RuleParams = dict[str, str | int]


class NicParams(TypedDict, total=False):
    connection_state: RuleParams
    dynamic_mac: RuleParams
    expected_vswitch: RuleParams


hyperv_vm_nic_default_params: Final[NicParams] = {
    "connection_state": {
        "connected": "true",
        "state_if_not_expected": State.WARN.value,
    },
    "dynamic_mac": {
        "dynamic_mac_enabled": "true",
        "state_if_not_expected": State.OK.value,
    },
    "expected_vswitch": {
        "name": "",
        "state_if_not_expected": State.OK.value,
    },
}


def parse_hyperv_vm_nic(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, str]] = {}

    if len(string_table) == 0:
        return parsed

    current_nic_data: dict[str, str] = {}
    nic_id = ""

    for line in string_table:
        field_name, *field_values = line
        match field_name:
            case "nic.name":
                # Save previous NIC if we have complete data
                if current_nic_data and nic_id:
                    parsed[nic_id] = current_nic_data

                # Start new NIC
                current_nic_data = {}
                nic_id = ""
                current_nic_data[field_name] = " ".join(field_values)

            case "nic.id":
                full_id = " ".join(field_values)
                current_nic_data[field_name] = full_id

                # Extract the GUID part after the backslash to use as service name
                if "\\" in full_id:
                    nic_id = full_id.split("\\")[-1]
                else:
                    nic_id = full_id

            case "nic":
                # Skip the "nic X" line - we don't need it since we use nic.name as separator
                continue

            case _:
                current_nic_data[field_name] = " ".join(field_values)

    # Don't forget the last NIC
    if current_nic_data and nic_id:
        parsed[nic_id] = current_nic_data

    return parsed


def discovery_hyperv_vm_nic(section: Section) -> DiscoveryResult:
    for key, values in section.items():
        if "nic.name" in values:
            yield Service(item=key)


def _check_field(
    data: Mapping[str, str],
    field: str,
    default: str,
    error_condition: Callable[[str], bool],
    error_msg: str,
    success_msg_template: str,
) -> Result:
    value = data.get(field, default)

    if error_condition(value):
        return Result(state=State.WARN, summary=error_msg)
    else:
        return Result(state=State.OK, summary=success_msg_template.format(value))


def _check_connection_state(data: Mapping[str, str], params: NicParams, item: str) -> CheckResult:
    if "connection_state" not in params:
        actual_state = data.get("nic.connectionstate", "unknown")
        yield Result(state=State.OK, summary=f"Connected: {actual_state}")
        return

    connection_params = params["connection_state"]
    expected_state = connection_params["connected"]
    actual_state = data.get("nic.connectionstate", "unknown")

    if actual_state == "unknown":
        yield Result(state=State.UNKNOWN, summary=f"Connection state missing for NIC: {item}")
        return

    if actual_state.lower() == expected_state:
        state = State.OK
    else:
        state = State(connection_params["state_if_not_expected"])

    yield Result(state=state, summary=f"Connected: {actual_state}")


def _check_mac_configuration(data: Mapping[str, str], params: NicParams, item: str) -> CheckResult:
    if "dynamic_mac" not in params:
        actual_dynamic_mac = data.get("nic.dynamicMAC", "unknown")
        yield Result(state=State.OK, summary=f"Dynamic MAC: {actual_dynamic_mac}")
        return

    dynamic_mac_params = params["dynamic_mac"]
    expected_dynamic_mac = dynamic_mac_params["dynamic_mac_enabled"]
    actual_dynamic_mac = data.get("nic.dynamicMAC", "unknown")

    if actual_dynamic_mac == "unknown":
        yield Result(state=State.UNKNOWN, summary=f"Dynamic MAC missing for NIC: {item}")
        return

    if actual_dynamic_mac.lower() == expected_dynamic_mac:
        state = State.OK
    else:
        state = State(dynamic_mac_params["state_if_not_expected"])

    yield Result(state=state, summary=f"Dynamic MAC: {actual_dynamic_mac}")


def _check_vswitch(data: Mapping[str, str], params: NicParams, item: str) -> CheckResult:
    if "expected_vswitch" not in params:
        actual_vswitch_name = data.get("nic.vswitch", "unknown")
        yield Result(state=State.OK, summary=f"Virtual switch: {actual_vswitch_name}")
        return

    vswitch_params = params["expected_vswitch"]
    expected_vswitch_name = vswitch_params["name"]
    actual_vswitch_name = data.get("nic.vswitch", "unknown")

    if actual_vswitch_name == "unknown":
        yield Result(state=State.UNKNOWN, summary=f"Virtual switch missing for NIC: {item}")
        return

    if actual_vswitch_name == expected_vswitch_name:
        state = State.OK
    else:
        state = State(vswitch_params["state_if_not_expected"])

    yield Result(state=state, summary=f"Virtual switch: {actual_vswitch_name}")


def check_hyperv_vm_nic(item: str, params: NicParams, section: Section) -> CheckResult:
    data = section.get(item)
    if not data:
        yield Result(state=State.WARN, summary=f"NIC information is missing: {item}")
        return

    nic_name = data.get("nic.name", "Unknown NIC")
    yield Result(state=State.OK, summary=f"Name: {nic_name}")

    yield from _check_connection_state(data, params, item)

    yield from _check_mac_configuration(data, params, item)

    yield from _check_vswitch(data, params, item)

    yield _check_field(
        data=data,
        field="nic.VLAN.mode",
        default="no VLAN mode",
        error_condition=lambda x: x == "no VLAN mode",
        error_msg=f"VLAN mode missing for NIC: {item}",
        success_msg_template="VLAN mode: {}",
    )

    yield _check_field(
        data=data,
        field="nic.VLAN.id",
        default="no VLAN ID",
        error_condition=lambda x: x == "no VLAN ID",
        error_msg=f"VLAN ID missing for NIC: {item}",
        success_msg_template="VLAN ID: {}",
    )


agent_section_hyperv_vm_nic = AgentSection(
    name="hyperv_vm_nic",
    parse_function=parse_hyperv_vm_nic,
)

check_plugin_hyperv_vm_nic = CheckPlugin(
    name="hyperv_vm_nic",
    service_name="HyperV NIC %s",
    sections=["hyperv_vm_nic"],
    discovery_function=discovery_hyperv_vm_nic,
    check_function=check_hyperv_vm_nic,
    check_default_parameters=hyperv_vm_nic_default_params,
    check_ruleset_name="hyperv_vm_nic",
)
