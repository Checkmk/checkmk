#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
from collections.abc import Sequence
from typing import Literal, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.proxmox_ve.lib.replication import Replication, SectionReplication


class Params(TypedDict):
    time_since_last_replication: NoLevelsT | FixedLevelsT[float]
    no_replications_state: Literal[0, 1, 2, 3]


def parse_proxmox_ve_replication(string_table: StringTable) -> SectionReplication:
    return SectionReplication.model_validate_json(json.loads(string_table[0][0]))


agent_section_proxmox_ve_replication = AgentSection(
    name="proxmox_ve_replication",
    parse_function=parse_proxmox_ve_replication,
)


def discover_proxmox_ve_replication(section: SectionReplication) -> DiscoveryResult:
    yield Service()


def _check_replications_with_no_errors(
    now: float,
    replications: Sequence[Replication],
    upper_levels: FixedLevelsT[float] | NoLevelsT,
) -> CheckResult:
    yield Result(
        state=State.OK,
        summary="All replications OK",
    )
    yield from check_levels(
        value=now - max(repl.last_sync for repl in replications),
        levels_upper=upper_levels,
        render_func=render.timespan,
        label="Time since last replication",
    )


def check_proxmox_ve_replication(params: Params, section: SectionReplication) -> CheckResult:
    if not section.cluster_has_replications:
        yield Result(
            state=State(params["no_replications_state"]),
            summary="Replication jobs not configured",
        )
        return

    if not section.replications:
        yield Result(state=State.OK, summary="No replication jobs found")
        return

    errors = [repl for repl in section.replications if repl.error]
    if errors:
        yield Result(
            state=State.CRIT,
            summary=f"Replication job: {errors[0].id}: {errors[0].error}",
            details="\n".join(f"{repl.id}: {repl.error}" for repl in errors[1:]) or None,
        )
        return

    yield from _check_replications_with_no_errors(
        now=datetime.datetime.now().timestamp(),
        replications=section.replications,
        upper_levels=params["time_since_last_replication"],
    )


check_plugin_proxmox_ve_replication = CheckPlugin(
    name="proxmox_ve_replication",
    service_name="Proxmox VE Replication",
    discovery_function=discover_proxmox_ve_replication,
    check_function=check_proxmox_ve_replication,
    check_ruleset_name="proxmox_ve_replication",
    check_default_parameters={
        "time_since_last_replication": ("no_levels", None),
        "no_replications_state": 1,
    },
)
