#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Sequence[int]]


def parse_proxmox_ve_snapshot_age(string_table: StringTable) -> Section:
    section = json.loads(string_table[0][0])
    return section


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_snapshot_age(params: Mapping[str, Any], section: Section) -> CheckResult:
    if not section["snaptimes"]:
        yield Result(state=State.OK, summary="No snapshot found")
        return

    # timestamps and timezones...
    age = max(time.time() - min(section["snaptimes"]), 0)

    yield from check_levels(
        age,
        levels_upper=params["oldest_levels"],
        metric_name="age",
        render_func=render.timespan,
        label="Age",
        boundaries=params["oldest_levels"][1],
    )


agent_section_proxmox_ve_vm_snapshot_age = AgentSection(
    name="proxmox_ve_vm_snapshot_age",
    parse_function=parse_proxmox_ve_snapshot_age,
)

check_plugin_proxmox_ve_vm_snapshot_age = CheckPlugin(
    name="proxmox_ve_vm_snapshot_age",
    service_name="Proxmox VE VM Snapshot age",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_snapshot_age,
    check_ruleset_name="proxmox_ve_vm_snapshot_age",
    check_default_parameters={
        "oldest_levels": ("fixed", (60.0 * 60.0 * 24.0 * 1.0, 60.0 * 60.0 * 24.0 * 2.0))
    },
)
