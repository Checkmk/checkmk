#!/usr/bin/python
# # -*- encoding: utf-8; py-indent-offset: 4 -*-

import time
from collections.abc import Mapping
from typing import Any, Dict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    render,
)
from cmk.plugins.hyperv.lib import parse_hyperv

Section = Dict[str, Mapping[str, Any]]


def discovery_hyperv_vm_checkpoints(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_hyperv_vm_checkpoints(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    if len(section) > 0:
        last_checkpoint = float("inf")
        last_checkpoint_name = ""
        oldest_checkpoint = 0

        for checkpoint in section:
            checkpoint_date = section[checkpoint].get("checkpoint.created")
            checkpoint_time = time.strptime(checkpoint_date, "%d.%m.%Y %H:%M:%S")
            checkpoint_age = time.time() - time.mktime(checkpoint_time)
            if checkpoint_age > oldest_checkpoint:
                oldest_checkpoint = checkpoint_age
                oldest_checkpoint_name = checkpoint
            if checkpoint_age < last_checkpoint:
                last_checkpoint = checkpoint_age
                last_checkpoint_name = checkpoint

        if params.get("age_oldest"):
            warn, crit = params["age_oldest"]
            if crit < warn:
                crit = float("inf")
            if oldest_checkpoint > crit:
                message = f"Oldest Checkpoint is older than {render.timespan(crit)}"
                yield Result(state=State(2), summary=message)
            elif oldest_checkpoint > warn:
                message = f"Oldest Checkpoint is older than {render.timespan(warn)}"
                yield Result(state=State(1), summary=message)
                yield Metric(
                    name="age_oldest",
                    value=oldest_checkpoint,
                    levels=(warn, crit),
                )

        if params.get("age"):
            warn, crit = params["age"]
            if crit < warn:
                crit = float("inf")
            if last_checkpoint > crit:
                message = f"Last Checkpoint is older than { render.timespan(crit)}"
                yield Result(state=State(2), summary=message)
            elif last_checkpoint > warn:
                message = f"Last Checkpoint is older than {render.timespan(warn)}"
                yield Result(state=State(1), summary=message)
                yield Metric(
                    name="age_last",
                    value=last_checkpoint,
                    levels=(warn, crit),
                )
        else:
            message = f"Last Checkpoint: {last_checkpoint_name} is {render.timespan(last_checkpoint)} old"

        yield Result(state=State(0), summary=message)

        yield Metric(
            name="age_last",
            value=last_checkpoint,
        )

    else:
        yield Result(state=State(0), summary="No Checkpoints existing")


agent_section_hyperv_vm_checkpoints = AgentSection(
    name="hyperv_vm_checkpoints",
    parse_function=parse_hyperv,
)

check_plugin_hyperv_vm_checkpoints = CheckPlugin(
    name="hyperv_vm_checkpoints",
    service_name="HyperV Checkpoints",
    sections=["hyperv_vm_checkpoints"],
    check_default_parameters={},
    discovery_function=discovery_hyperv_vm_checkpoints,
    check_function=check_hyperv_vm_checkpoints,
    check_ruleset_name="vm_snapshots",
)
