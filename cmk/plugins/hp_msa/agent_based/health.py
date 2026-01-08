#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State

# TODO
# Use 'status-numeric' instead of 'status' field regardless of language.
# See for state mapping: https://support.hpe.com/hpsc/doc/public/display?docId=emr_na-a00017709en_us

_HealthSection = Mapping[str, Mapping[str, str]]

_STATE_MAP = {
    "0": (State.OK, "OK"),
    "1": (State.WARN, "degraded/warning"),
    "2": (State.CRIT, "fault/error"),
    "3": (State.UNKNOWN, "unknown"),
    "4": (State.CRIT, "not present"),
}


def discover_hp_msa_health(section: _HealthSection) -> DiscoveryResult:
    yield from (Service(item=key) for key in section)


def check_hp_msa_health(item: str, section: _HealthSection) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    health_state, health_state_readable = _STATE_MAP[data["health-numeric"]]
    health_info = "Status: %s" % health_state_readable
    if health_state is not State.OK and data.get("health-reason", ""):
        health_info += " (%s)" % data["health-reason"]

    yield Result(state=health_state, summary=health_info)

    # extra info of volumes
    if data["item_type"] == "volumes":
        volume_info = data.get("container-name", "")
        if volume_info:
            if data.get("raidtype", ""):
                volume_info += " (%s)" % data["raidtype"]
            yield Result(state=State.OK, summary=f"Container name: {volume_info}")
        return

    # extra info of disks
    if data["item_type"] == "drives":
        for disk_info in ["serial-number", "vendor", "model", "description", "size"]:
            if data.get(disk_info, ""):
                yield Result(
                    state=State.OK,
                    summary=f"{disk_info.replace('-', ' ').capitalize()}: {data[disk_info].replace('GB', ' GB')}",
                )

        if data.get("rpm", ""):
            yield Result(state=State.OK, summary=f"Speed: {data['rpm']} RPM")
