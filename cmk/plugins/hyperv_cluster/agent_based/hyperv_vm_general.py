#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

# Thanks to Andreas Döhler for the contribution.

from collections.abc import Mapping
from typing import Final, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.hyperv_cluster.lib import hyperv_vm_convert

Section = Mapping[str, str]


class GeneralParams(TypedDict):
    power_state: dict[str, int]
    vm_generation: dict[str, str | int]


hyperv_vm_general_default_params: Final[GeneralParams] = {
    "power_state": {
        "running": State.OK.value,
        "off": State.CRIT.value,
        "saved": State.OK.value,
        "paused": State.WARN.value,
        "starting": State.WARN.value,
    },
    "vm_generation": {
        "expected_generation": "generation_2",
        "state_if_not_expected": State.WARN.value,
    },
}


def discovery_hyperv_vm_general(section: Section) -> DiscoveryResult:
    if "name" in section:
        yield Service()


def _check_power_state(section: Section, params: GeneralParams) -> CheckResult:
    power_state = section.get("runtime.powerState")
    if not power_state:
        yield Result(state=State.WARN, summary="State information is missing")
        return

    power_state_mapping = params["power_state"]
    state_value = power_state_mapping.get(power_state.lower(), State.UNKNOWN.value)
    yield Result(state=State(state_value), summary=f"State: {power_state}")


def _check_vm_generation(section: Section, params: GeneralParams) -> CheckResult:
    generation = section.get("config.generation")
    vm_generation_params = params["vm_generation"]

    if not generation or "expected_generation" not in vm_generation_params:
        yield Result(state=State.WARN, summary="VM Generation information is missing")
        return

    expected_generation = str(vm_generation_params["expected_generation"])
    expected_gen_number = expected_generation.replace("generation_", "")

    if generation != expected_gen_number:
        generation_state = State(
            vm_generation_params.get("state_if_not_expected", State.WARN.value)
        )
    else:
        generation_state = State.OK

    yield Result(state=generation_state, summary=f"VM Generation: {generation}")


def check_hyperv_vm_general(params: GeneralParams, section: Section) -> CheckResult:
    name = section.get("name")
    if not name:
        yield Result(state=State.WARN, summary="VM name information is missing")
        return
    else:
        yield Result(state=State.OK, summary=f"VM name: {name}")

    yield from _check_power_state(section, params)

    running_on = section.get("runtime.host")
    if not running_on:
        yield Result(state=State.WARN, summary="Host information is missing")
    else:
        yield Result(state=State.OK, summary=f"Host: {running_on}")

    yield from _check_vm_generation(section, params)


agent_section_hyperv_vm_general: AgentSection = AgentSection(
    name="hyperv_vm_general",
    parse_function=hyperv_vm_convert,
)

check_plugin_hyperv_vm_general = CheckPlugin(
    name="hyperv_vm_general",
    service_name="Hyper-V VM summary",
    sections=["hyperv_vm_general"],
    discovery_function=discovery_hyperv_vm_general,
    check_function=check_hyperv_vm_general,
    check_default_parameters=hyperv_vm_general_default_params,
    check_ruleset_name="hyperv_vm_general",
)
