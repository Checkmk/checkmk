#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from typing import Any, Mapping, NamedTuple, Sequence

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import esx_vsphere


class Snapshot(NamedTuple):
    time: int
    state: str
    name: str


Section = Sequence[Snapshot]


def parse_esx_vsphere_snapshots(string_table: StringTable) -> Section:
    """
    >>> parse_esx_vsphere_snapshots([
    ...     ['{"time": 0, "state": "poweredOn", "name": "foo"}'],
    ... ])
    [Snapshot(time=0, state='poweredOn', name='foo')]
    """
    return [Snapshot(**json.loads(line[0])) for line in string_table]


register.agent_section(
    name="esx_vsphere_snapshots_summary",
    parse_function=parse_esx_vsphere_snapshots,
)


def discover_snapshots_summary(section: Section) -> DiscoveryResult:
    yield Service()


def check_snapshots_summary(params: Mapping[str, Any], section: Section) -> CheckResult:
    snapshots = section  # just to be clear

    # use UTC-timestamp - don't use time.time() here since it's local
    now = int(datetime.datetime.utcnow().timestamp())

    if any(s for s in snapshots if s.time > now):
        yield Result(
            state=State.WARN,
            summary="Snapshot with a creation time in future found. Please check your network time synchronisation.",
        )
        return

    yield Result(state=State.OK, summary=f"Count: {len(snapshots)}")

    if not section:
        return

    powered_on = (s.name for s in snapshots if s.state == "poweredOn")
    yield Result(state=State.OK, summary="Powered on: %s" % (", ".join(powered_on) or "None"))

    latest_snapshot = max(snapshots, key=lambda s: s.time)
    latest_timestamp = render.datetime(latest_snapshot.time)
    oldest_snapshot = min(snapshots, key=lambda s: s.time)
    oldest_timestamp = render.datetime(oldest_snapshot.time)

    yield Result(state=State.OK, summary=f"Latest: {latest_snapshot.name} {latest_timestamp}")

    yield from check_levels(
        now - latest_snapshot.time,
        metric_name="age" if params.get("age") else None,
        levels_upper=params.get("age"),
        label="Age of latest",
        render_func=render.timespan,
        notice_only=True,
        boundaries=(0, None),
    )

    # Display oldest snapshot only, if it is not identical with the latest snapshot
    if oldest_snapshot != latest_snapshot:
        yield Result(state=State.OK, summary=f"Oldest: {oldest_snapshot.name} {oldest_timestamp}")
    # check oldest age unconditionally
    yield from check_levels(
        now - oldest_snapshot.time,
        metric_name="age_oldest" if params.get("age_oldest") else None,
        levels_upper=params.get("age_oldest"),
        label="Age of oldest",
        render_func=render.timespan,
        notice_only=True,
        boundaries=(0, None),
    )


register.check_plugin(
    name="esx_vsphere_vm_snapshots_summary",
    sections=["esx_vsphere_snapshots_summary"],
    service_name="ESX Snapshots Summary",
    discovery_function=discover_snapshots_summary,
    check_function=check_snapshots_summary,
    check_default_parameters={},
    check_ruleset_name="vm_snapshots",
)


def discover_snapshots(section: esx_vsphere.SectionVM) -> DiscoveryResult:
    yield Service()


def check_snapshots(params: Mapping[str, Any], section: esx_vsphere.SectionVM) -> CheckResult:
    raw_snapshots = " ".join(section.get("snapshot.rootSnapshotList", [])).split("|")
    iter_snapshots_tuple = (x.split(" ", 3) for x in raw_snapshots if x)
    yield from check_snapshots_summary(
        params, [Snapshot(int(x[1]), x[2], x[3]) for x in iter_snapshots_tuple]
    )


register.check_plugin(
    name="esx_vsphere_vm_snapshots",
    sections=["esx_vsphere_vm"],
    service_name="ESX Snapshots",
    discovery_function=discover_snapshots,
    check_function=check_snapshots,
    check_default_parameters={},
    check_ruleset_name="vm_snapshots",
)
