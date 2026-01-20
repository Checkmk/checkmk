#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"

# Example output from agent:
# <<<hyperv_vms>>>
# DMZ-DC1                         Running 4.21:44:58          Operating normally
# DMZ-DC2                         Running 4.21:44:47          Operating normally

# Another example, here with a snapshow with spaces in the name:
# <<<hyperv_vms>>>
# windows-hyperv2-z4058044                              Running 21:33:08   Operating normally
# windows-hyperv2-z4058044_snap (23.05.2014 - 09:29:29) Running 18:20:34   Operating normally
# windows-hyperv2-z4065002                              Running 11:04:50   Operating normally
# windows-hyperv2-z4065084                              Running 1.10:42:33 Operating normally
# windows-hyperv2-z4133235                              Running 1.03:52:18 Operating normally

# A broken version of the agent outputted this:
# <<<hyperv_vms>>>
# z4058044                        Running 21:19:14            Operating normally
# z4058044_snap (2...             Running 18:06:39            Operating normally
# z4065002                        Running 10:50:55            Operating normally
# z4065084                        Running 1.10:28:39          Operating normally
# z4133235                        Running 1.03:38:23          Operating normally

# A Version with a plug-in that uses tab as seperator and quotes the strings:
# <<<hyperv_vms:sep(9)>>>
# "Name"  "State" "Uptime"        "Status"
# "z4058013"      "Running"       "06:05:16"      "Operating normally"
# "z4058020"      "Running"       "01:01:57"      "Operating normally"
# "z4058021"      "Running"       "01:02:11"      "Operating normally"
# "z4065012"      "Running"       "01:02:04"      "Operating normally"
# "z4065013"      "Running"       "07:47:27"      "Operating normally"
# "z4065020"      "Running"       "01:02:09"      "Operating normally"
# "z4065025"      "Running"       "01:02:05"      "Operating normally"
# "z4133199"      "Running"       "00:57:23"      "Operating normally"

# result:
# {
#   "windows-hyperv2-z4058044_snap (23.05.2014 - 09:29:29)" : {
#        "vm_state" : "Running",
#        "uptime" : "1.10:42:33",
#        "state_msg" : "Operating normally",
#    }
# }

# these default values were suggested by Aldi Sued


from collections.abc import Mapping
from typing import Any

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

VMData = Mapping[str, Mapping[str, str]]


def parse_hyperv_vms(string_table: StringTable) -> VMData:
    parsed = {}
    for line in string_table:
        if len(line) != 4:
            # skip lines containing invalid data like e.g.
            # ../tests/unit/checks/generictests/datasets/hyperv_vms.py, line 16 or 17
            continue
        # Remove quotes
        line = [x.strip('"') for x in line]
        if line[1].endswith("..."):  # broken output
            vm_name = line[0]
            line = line[2:]
        elif line[1].startswith("("):
            idx = 2
            while idx < len(line):
                if line[idx].endswith(")"):
                    vm_name = " ".join(line[: idx + 1])
                    break
                idx += 1
            line = line[idx + 1 :]
        else:
            vm_name = line[0]
            line = line[1:]

        if ":" in line[1]:  # skip heading line
            parsed[vm_name] = {
                "state": line[0],
                "uptime": line[1],
                "state_msg": " ".join(line[2:]),
            }
    return parsed


def discover_hyperv_vms(section: VMData) -> DiscoveryResult:
    for vm_name, vm in section.items():
        yield Service(item=vm_name, parameters={"discovered_state": vm["state"]})


def check_hyperv_vms(item: str, params: Mapping[str, Any], section: VMData) -> CheckResult:
    if not (vm := section.get(item)):
        return

    compare_mode = params["vm_target_state"][0]

    if compare_mode == "discovery":
        discovered_state = params.get("discovered_state")

        # this means that the check is executed as a manual check
        if discovered_state is None:
            yield Result(
                state=State.UNKNOWN,
                summary=f"State is {vm['state']} ({vm['state_msg']}), discovery state is not available",
            )
            return

        if vm["state"] == discovered_state:
            yield Result(
                state=State.OK,
                summary=f"State {vm['state']} ({vm['state_msg']}) matches discovery",
            )
            return

        yield Result(
            state=State.CRIT,
            summary=f"State {vm['state']} ({vm['state_msg']}) does not match discovery ({discovered_state})",
        )
        return

    # service state defined in rule
    target_states = DEFAULT_STATE_MAPPING | params["vm_target_state"][1]
    service_state = target_states.get(vm["state"])

    # as a precaution, if in the future there are new VM states we do not know about
    if service_state is None:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Unknown state {vm['state']} ({vm['state_msg']})",
        )
    else:
        yield Result(
            state=State(service_state), summary=f"State is {vm['state']} ({vm['state_msg']})"
        )


DEFAULT_STATE_MAPPING = {
    "FastSaved": 0,
    "FastSavedCritical": 2,
    "FastSaving": 0,
    "FastSavingCritical": 2,
    "Off": 1,
    "OffCritical": 2,
    "Other": 3,
    "Paused": 0,
    "PausedCritical": 2,
    "Pausing": 0,
    "PausingCritical": 2,
    "Reset": 1,
    "ResetCritical": 2,
    "Resuming": 0,
    "ResumingCritical": 2,
    "Running": 0,
    "RunningCritical": 2,
    "Saved": 0,
    "SavedCritical": 2,
    "Saving": 0,
    "SavingCritical": 2,
    "Starting": 0,
    "StartingCritical": 2,
    "Stopping": 1,
    "StoppingCritical": 2,
}

DEFAULT_PARAMETERS = {
    "vm_target_state": (
        "map",
        DEFAULT_STATE_MAPPING,
    ),
}
agent_section_hyperv_vms = AgentSection(
    name="hyperv_vms",
    parse_function=parse_hyperv_vms,
)


check_plugin_hyperv_vms = CheckPlugin(
    name="hyperv_vms",
    service_name="VM %s",
    discovery_function=discover_hyperv_vms,
    check_function=check_hyperv_vms,
    check_ruleset_name="hyperv_vms",
    check_default_parameters=DEFAULT_PARAMETERS,
)
