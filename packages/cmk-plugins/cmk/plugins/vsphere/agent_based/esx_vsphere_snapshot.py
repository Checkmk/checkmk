#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.vsphere.lib import esx_vsphere


@dataclass(frozen=True)
class Snapshot:
    time: int
    systime: int | None
    state: str
    name: str
    vm: str | None = None

    @property
    def age(self) -> int | None:
        if self.systime is None:
            return None
        return self.systime - self.time


Section = Sequence[Snapshot]


def parse_esx_vsphere_snapshots(string_table: StringTable) -> Section:
    """
    >>> parse_esx_vsphere_snapshots([
    ...     ['{"time": 0, "systime": 0, "state": "poweredOn", "name": "foo", "vm": "bar"}'],
    ... ])
    [Snapshot(time=0, systime=0, state='poweredOn', name='foo', vm='bar')]
    """
    return [Snapshot(**json.loads(line[0])) for line in string_table]


agent_section_esx_vsphere_snapshots_summary = AgentSection(
    name="esx_vsphere_snapshots_summary",
    parse_function=parse_esx_vsphere_snapshots,
)


def discover_snapshots_summary(section: Section) -> DiscoveryResult:
    yield Service()


def _get_snapshot_name(snapshot: Snapshot) -> str:
    return f"{snapshot.vm}/{snapshot.name}" if snapshot.vm else snapshot.name


def check_snapshots_summary(params: Mapping[str, Any], section: Section) -> CheckResult:
    snapshots = section  # just to be clear

    if any(s for s in snapshots if s.age is not None and s.age < 0):
        yield Result(
            state=State.WARN,
            summary="Snapshot with a creation time in future found. Please check your network time synchronisation.",
        )
        return

    yield Result(state=State.OK, summary=f"Count: {len(snapshots)}")

    if not section:
        return

    powered_on = [_get_snapshot_name(s) for s in snapshots if s.state == "poweredOn"]
    yield Result(
        state=State.OK, summary=f"Powered on: {', '.join(powered_on) if powered_on else 'None'}"
    )

    latest_snapshot = max(snapshots, key=lambda s: s.time)
    latest_timestamp = render.datetime(latest_snapshot.time)
    oldest_snapshot = min(snapshots, key=lambda s: s.time)
    oldest_timestamp = render.datetime(oldest_snapshot.time)

    yield Result(
        state=State.OK,
        summary=f"Latest: {_get_snapshot_name(latest_snapshot)} {latest_timestamp}",
    )

    if latest_snapshot.age is not None:
        yield from check_levels_v1(
            latest_snapshot.age,
            metric_name="age" if params.get("age") else None,
            levels_upper=params.get("age"),
            label="Age of latest",
            render_func=render.timespan,
            notice_only=True,
            boundaries=(0, None),
        )

    # Display oldest snapshot only, if it is not identical with the latest snapshot
    if oldest_snapshot != latest_snapshot:
        yield Result(
            state=State.OK,
            summary=f"Oldest: {_get_snapshot_name(oldest_snapshot)} {oldest_timestamp}",
        )

    if oldest_snapshot.age is not None:
        yield from check_levels_v1(
            oldest_snapshot.age,
            metric_name="age_oldest" if params.get("age_oldest") else None,
            levels_upper=params.get("age_oldest"),
            label="Age of oldest",
            render_func=render.timespan,
            notice_only=True,
            boundaries=(0, None),
        )


check_plugin_esx_vsphere_vm_snapshots_summary = CheckPlugin(
    name="esx_vsphere_vm_snapshots_summary",
    sections=["esx_vsphere_snapshots_summary"],
    service_name="ESX Snapshots Summary",
    discovery_function=discover_snapshots_summary,
    check_function=check_snapshots_summary,
    check_default_parameters={},
    check_ruleset_name="vm_snapshots",
)


def discover_snapshots(section: esx_vsphere.SectionESXVm) -> DiscoveryResult:
    yield Service()


def check_snapshots(params: Mapping[str, Any], section: esx_vsphere.SectionESXVm) -> CheckResult:
    raw_snapshots = " ".join(section.snapshots).split("|")
    iter_snapshots_tuple = (x.split(" ", 3) for x in raw_snapshots if x)

    yield from check_snapshots_summary(
        params,
        [
            Snapshot(
                time=int(x[1]),
                systime=(int(section.systime) if (section.systime is not None) else None),
                state=x[2],
                name=x[3],
                vm=section.name if section.name else None,
            )
            for x in iter_snapshots_tuple
        ],
    )


check_plugin_esx_vsphere_vm_snapshots = CheckPlugin(
    name="esx_vsphere_vm_snapshots",
    sections=["esx_vsphere_vm"],
    service_name="ESX Snapshots",
    discovery_function=discover_snapshots,
    check_function=check_snapshots,
    check_default_parameters={},
    check_ruleset_name="vm_snapshots",
)
