#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.veeam.lib import parse_iso8601_epoch


@dataclass(frozen=True, kw_only=True)
class RestorePoint:
    creation_time: float | None
    type: str | None
    malware_status: str | None


@dataclass(frozen=True, kw_only=True)
class BackupObject:
    """A backup object (GET /api/v1/backupObjects), with its restore points
    (GET /api/v1/restorePoints) reduced by the special agent."""

    platform_name: str | None
    type: str | None
    restore_points_count: int | None
    last_restore_point: RestorePoint | None
    malware_status: str | None
    """The worst malware status across all restore points of the object."""


Section = Mapping[str, BackupObject]


class CheckParameters(TypedDict):
    age: LevelsT[float]


def _parse_restore_point(raw: Mapping[str, str | None] | None) -> RestorePoint | None:
    if raw is None:
        return None
    creation_time = raw["creationTime"]
    return RestorePoint(
        creation_time=parse_iso8601_epoch(creation_time) if creation_time is not None else None,
        type=raw["type"],
        malware_status=raw["malwareStatus"],
    )


def _item(name: str, platform_name: str | None) -> str:
    return name if platform_name is None else f"{platform_name} - {name}"


def parse_veeam_restore_points(string_table: StringTable) -> Section:
    section: dict[str, BackupObject] = {}
    for line in string_table:
        object_dict = json.loads(line[0])
        section[_item(object_dict["name"], object_dict["platformName"])] = BackupObject(
            platform_name=object_dict["platformName"],
            type=object_dict["type"],
            restore_points_count=object_dict["restorePointsCount"],
            last_restore_point=_parse_restore_point(object_dict["lastRestorePoint"]),
            malware_status=object_dict["malwareStatus"],
        )
    return section


def discovery_veeam_restore_points(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _malware_state(malware_status: str | None) -> State:
    match malware_status:
        case "Clean" | "Informative":
            return State.OK
        case "Suspicious":
            return State.WARN
        case "Infected":
            return State.CRIT
        case _:
            return State.UNKNOWN


def check_veeam_restore_points(item: str, params: CheckParameters, section: Section) -> CheckResult:
    if (backup_object := section.get(item)) is None:
        return

    if backup_object.restore_points_count is None:
        yield Result(state=State.UNKNOWN, summary="Number of restore points unknown")
    elif backup_object.restore_points_count == 0:
        yield Result(state=State.CRIT, summary="0 restore points")
    else:
        yield Result(state=State.OK, summary=f"{backup_object.restore_points_count} restore points")
        last = backup_object.last_restore_point
        if last is None or last.creation_time is None:
            yield Result(state=State.UNKNOWN, summary="Newest restore point not found")
        elif (age := time.time() - last.creation_time) < 0:
            yield Result(state=State.OK, summary="Last restore point is in the future")
        else:
            yield from check_levels(
                age,
                levels_upper=params["age"],
                render_func=lambda v: f"{render.timespan(v)} ago",
                label="last",
            )
        yield Result(
            state=_malware_state(backup_object.malware_status),
            notice=f"Malware status: {backup_object.malware_status or 'unknown'}",
        )

    yield Result(state=State.OK, notice=f"Platform: {backup_object.platform_name or 'unknown'}")
    yield Result(state=State.OK, notice=f"Object type: {backup_object.type or 'unknown'}")
    if (last := backup_object.last_restore_point) is not None:
        yield Result(state=State.OK, notice=f"Last restore point type: {last.type or 'unknown'}")
        yield Result(
            state=State.OK,
            notice=f"Last restore point malware status: {last.malware_status or 'unknown'}",
        )


agent_section_veeam_restore_points = AgentSection(
    name="veeam_restore_points",
    parse_function=parse_veeam_restore_points,
)

check_plugin_veeam_restore_points = CheckPlugin(
    name="veeam_restore_points",
    service_name="Restore points %s",
    discovery_function=discovery_veeam_restore_points,
    check_function=check_veeam_restore_points,
    check_ruleset_name="veeam_restore_points",
    # Carried over from the VEEAM Client check, so users moving over see the same levels.
    check_default_parameters=CheckParameters(age=("fixed", (30 * 3600.0, 48 * 3600.0))),
)
