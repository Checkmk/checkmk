#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, Sequence
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
    """The backed up machine of a piggyback host: its backup objects
    (GET /api/v1/backupObjects, one per job) merged by the special agent, with their
    restore points (GET /api/v1/restorePoints) reduced."""

    platform_name: str | None
    type: str | None
    restore_points_count: int | None
    last_restore_point: RestorePoint | None
    malware_status: str | None
    """The worst malware status across all restore points of the object. None if no
    restore point was scanned."""


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


def _parse_backup_object(raw: str) -> BackupObject:
    object_dict = json.loads(raw)
    return BackupObject(
        platform_name=object_dict["platformName"],
        type=object_dict["type"],
        restore_points_count=object_dict["restorePointsCount"],
        last_restore_point=_parse_restore_point(object_dict["lastRestorePoint"]),
        malware_status=object_dict["malwareStatus"],
    )


_MALWARE_SEVERITY = {"Clean": 0, "Informative": 1, "Suspicious": 2, "Infected": 3}


def _creation_time(backup_object: BackupObject) -> float:
    last = backup_object.last_restore_point
    return float("-inf") if last is None or last.creation_time is None else last.creation_time


def _merge(backup_objects: Sequence[BackupObject]) -> BackupObject:
    """Merges the records of one machine sent by several Veeam servers, the same way the
    special agent merges the backup objects of several jobs."""
    newest = max(backup_objects, key=_creation_time)
    counts = [backup_object.restore_points_count for backup_object in backup_objects]
    statuses = [o.malware_status for o in backup_objects if o.malware_status is not None]
    return BackupObject(
        platform_name=newest.platform_name,
        type=newest.type,
        restore_points_count=None if None in counts else sum(c for c in counts if c is not None),
        last_restore_point=newest.last_restore_point,
        malware_status=max(
            statuses,
            key=lambda status: _MALWARE_SEVERITY.get(status, len(_MALWARE_SEVERITY)),
            default=None,
        ),
    )


def parse_veeam_restore_points(string_table: StringTable) -> BackupObject | None:
    if not string_table:
        return None
    return _merge([_parse_backup_object(line[0]) for line in string_table])


def discovery_veeam_restore_points(section: BackupObject) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def _malware_state(malware_status: str) -> State:
    match malware_status:
        case "Clean" | "Informative":
            return State.OK
        case "Suspicious":
            return State.WARN
        case "Infected":
            return State.CRIT
        case _:
            return State.UNKNOWN


def check_veeam_restore_points(params: CheckParameters, section: BackupObject) -> CheckResult:
    if section.restore_points_count is None:
        yield Result(state=State.UNKNOWN, summary="Number of restore points unknown")
    elif section.restore_points_count == 0:
        yield Result(state=State.CRIT, summary="0 restore points")
    else:
        yield Result(state=State.OK, summary=f"{section.restore_points_count} restore points")
        last = section.last_restore_point
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
        if section.malware_status is None:
            yield Result(state=State.OK, notice="Malware status: not scanned")
        else:
            yield Result(
                state=_malware_state(section.malware_status),
                notice=f"Malware status: {section.malware_status}",
            )

    yield Result(state=State.OK, notice=f"Platform: {section.platform_name or 'unknown'}")
    yield Result(state=State.OK, notice=f"Object type: {section.type or 'unknown'}")
    if (last := section.last_restore_point) is not None:
        yield Result(state=State.OK, notice=f"Last restore point type: {last.type or 'unknown'}")
        yield Result(
            state=State.OK,
            notice=f"Last restore point malware status: {last.malware_status or 'not scanned'}",
        )


agent_section_veeam_restore_points = AgentSection(
    name="veeam_restore_points",
    parse_function=parse_veeam_restore_points,
)

check_plugin_veeam_restore_points = CheckPlugin(
    name="veeam_restore_points",
    service_name="Restore points",
    discovery_function=discovery_veeam_restore_points,
    check_function=check_veeam_restore_points,
    check_ruleset_name="veeam_restore_points",
    # Carried over from the VEEAM Client check, so users moving over see the same levels.
    check_default_parameters=CheckParameters(age=("fixed", (30 * 3600.0, 48 * 3600.0))),
)
