#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import Any, Mapping, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
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
        boundaries=params["oldest_levels"],
    )


register.agent_section(
    name="proxmox_ve_vm_snapshot_age",
    parse_function=parse_proxmox_ve_snapshot_age,
)

register.check_plugin(
    name="proxmox_ve_vm_snapshot_age",
    service_name="Proxmox VE VM Snapshot age",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_snapshot_age,
    check_ruleset_name="proxmox_ve_vm_snapshot_age",
    check_default_parameters={
        "oldest_levels": (
            60 * 60 * 24 * 1,
            60 * 60 * 24 * 2,
        )
    },
)
