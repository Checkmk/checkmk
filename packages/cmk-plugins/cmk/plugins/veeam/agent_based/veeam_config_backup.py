#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
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
class ConfigBackup:
    """Mirrors the VBR REST API's ConfigBackupSettingsModel (GET /api/v1/configBackup)."""

    is_enabled: bool
    last_successful_time: float | None
    restore_points_to_keep: int
    encryption_enabled: bool
    backup_repository_id: str


Section = ConfigBackup


class CheckParameters(TypedDict):
    disabled_state: int
    age: LevelsT[float]


def parse_veeam_config_backup(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    config_dict = json.loads(string_table[0][0])
    last_successful_backup = config_dict["lastSuccessfulBackup"]
    encryption = config_dict["encryption"]
    last_successful_time = last_successful_backup.get("lastSuccessfulTime")
    return ConfigBackup(
        is_enabled=config_dict["isEnabled"],
        last_successful_time=(
            parse_iso8601_epoch(last_successful_time) if last_successful_time is not None else None
        ),
        restore_points_to_keep=config_dict["restorePointsToKeep"],
        encryption_enabled=encryption["isEnabled"],
        backup_repository_id=config_dict["backupRepositoryId"],
    )


def discovery_veeam_config_backup(section: Section) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_veeam_config_backup(params: CheckParameters, section: Section) -> CheckResult:
    if not section.is_enabled:
        yield Result(
            state=State(params["disabled_state"]),
            summary="Configuration backup disabled",
        )
        return

    if section.last_successful_time is None:
        yield Result(
            state=State.CRIT,
            summary="No successful backup yet",
        )
    else:
        yield from check_levels(
            time.time() - section.last_successful_time,
            levels_upper=params["age"],
            metric_name="veeam_config_backup_age",
            render_func=lambda v: (
                render.timespan(v) if v >= 0 else "last successful backup is in the future"
            ),
            label="Time since last successful backup",
        )

    yield Result(
        state=State.OK,
        summary=f"Restore points kept: {section.restore_points_to_keep}",
    )
    yield Result(
        state=State.OK,
        summary=f"Encryption: {'enabled' if section.encryption_enabled else 'disabled'}",
    )
    yield Result(
        state=State.OK,
        summary=f"Target repository ID: {section.backup_repository_id}",
    )


agent_section_veeam_config_backup = AgentSection(
    name="veeam_config_backup",
    parse_function=parse_veeam_config_backup,
)

check_plugin_veeam_config_backup = CheckPlugin(
    name="veeam_config_backup",
    service_name="Configuration backup",
    discovery_function=discovery_veeam_config_backup,
    check_function=check_veeam_config_backup,
    check_ruleset_name="veeam_config_backup",
    # TODO: thresholds are proposed and unvalidated. The reference PowerShell
    # implementation instead uses 7/14 days, looser than a daily backup schedule
    # warrants — this disagreement needs settling.
    check_default_parameters=CheckParameters(
        disabled_state=1,
        age=("fixed", (48 * 3600.0, 96 * 3600.0)),
    ),
)
