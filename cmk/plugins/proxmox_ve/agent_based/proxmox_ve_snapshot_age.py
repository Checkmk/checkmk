#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, Field

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


class SectionSnapshots(BaseModel, frozen=True):
    snaptimes: Sequence[int] = Field(alias="snaptimes", default_factory=list)


def parse_proxmox_ve_snapshot_age(string_table: StringTable) -> SectionSnapshots:
    return SectionSnapshots.model_validate_json(string_table[0][0])


def discover_single(section: SectionSnapshots) -> DiscoveryResult:
    yield Service()


def _check_proxmox_ve_snapshot_age_testable(
    now: float, params: Mapping[str, Any], snaptimes: Sequence[int]
) -> CheckResult:
    # timestamps and timezones...
    oldest_snapshot = max(now - min(snaptimes), 0)
    newest_snapshot = max(now - max(snaptimes), 0)

    yield from check_levels(
        oldest_snapshot,
        label="Oldest",
        levels_upper=params["oldest_levels"],
        metric_name="oldest_snapshot_age",
        render_func=render.timespan,
        boundaries=params["oldest_levels"][1],
    )

    yield from check_levels(
        newest_snapshot,
        label="Newest",
        levels_upper=params.get("newest_levels"),
        boundaries=params.get("newest_levels", (None, None))[1],
        metric_name="newest_snapshot_age",
        render_func=render.timespan,
    )

    yield Result(state=State.OK, summary=f"Snapshots: {len(snaptimes)}")


def check_proxmox_ve_snapshot_age(
    params: Mapping[str, Any], section: SectionSnapshots
) -> CheckResult:
    if not section.snaptimes:
        yield Result(state=State.OK, summary="No snapshot found")
        return

    yield from _check_proxmox_ve_snapshot_age_testable(
        datetime.datetime.now(tz=datetime.UTC).timestamp(),
        params,
        section.snaptimes,
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
