#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent on success:
# <<<timemachine>>>
# /Volumes/Backup/Backups.backupdb/macvm/2013-11-28-202610
#
# Example output from agent on failure:
# <<<timemachine>>>
# Unable to locate machine directory for host.
import datetime
from collections.abc import Mapping
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


def parse_timemachine(string_table: StringTable) -> str:
    return " ".join(string_table[0])


agent_section_timemachine = AgentSection(
    name="timemachine",
    parse_function=parse_timemachine,
)


def discover_timemachine(section: str) -> DiscoveryResult:
    if section != "Unable to locate machine directory for host.":
        yield Service()


def check_timemachine(params: Mapping[str, Any], section: str) -> CheckResult:
    yield from _check(datetime.datetime.now(), params, section)


def _check(now: datetime.datetime, params: Mapping[str, Any], section: str) -> CheckResult:
    # We expect at least one line
    if not section.startswith("/Volumes/"):
        yield Result(
            state=State.CRIT, summary=f"Backup seems to have failed, message was: {section}"
        )
        return

    raw_backup_time = section.split("/")[-1].removesuffix(".backup")
    backup_time = datetime.datetime.strptime(raw_backup_time, "%Y-%m-%d-%H%M%S")
    backup_age = (now - backup_time).total_seconds()

    if backup_age < 0:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Timestamp of last backup is in the future: {datetime.datetime.strftime(backup_time, '%Y-%m-%d %H:%M:%S')}",
        )
        return

    yield from check_levels_v1(
        value=backup_age,
        levels_upper=params["age"],
        label=f"Last backup was at {datetime.datetime.strftime(backup_time, '%Y-%m-%d %H:%M:%S')}",
        render_func=lambda a: f"{render.timespan(a)} ago",
    )


check_plugin_timemachine = CheckPlugin(
    name="timemachine",
    check_function=check_timemachine,
    discovery_function=discover_timemachine,
    check_default_parameters={"age": (86400, 172800)},  # 1d/2d
    service_name="Backup Timemachine",
    check_ruleset_name="backup_timemachine",
)
