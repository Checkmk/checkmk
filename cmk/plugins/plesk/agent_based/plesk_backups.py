#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
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

Section = Mapping[str, Sequence[str]]


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_plesk_backups(string_table: StringTable) -> Section:
    return {line[0]: line for line in string_table}


def discover_plesk_backups(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_plesk_backups(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (line := section.get(item)) is None:
        return

    if len(line) != 5 or line[1] != "0":
        match line[1]:
            case "2":
                yield Result(state=State.UNKNOWN, summary=f"Error in agent ({' '.join(line[1:])})")
            case "4":
                yield Result(
                    state=State(int(params.get("no_backup_configured_state", 1))),
                    summary="No backup configured",
                )
            case "5":
                yield Result(
                    state=State(int(params.get("no_backup_found_state", 1))),
                    summary="No backup found",
                )
            case _:
                yield Result(state=State.UNKNOWN, summary=f"Unexpected line {line!r}")
        return

    _domain, _rc, r_timestamp, r_size, r_total_size = line
    size = saveint(r_size)
    total_size = saveint(r_total_size)
    timestamp = saveint(r_timestamp)

    # 1. check last backup size not 0 bytes
    yield from check_levels(
        size,
        "last_backup_size",
        (None, None, 0, 0),
        infoname="Last Backup - Size",
        human_readable_func=render.disksize,
    )
    # 2. check age of last backup < 24h
    age_seconds = int(time.time()) - timestamp
    yield from check_levels(
        age_seconds,
        "last_backup_age",
        params.get("backup_age"),
        infoname="Age",
        human_readable_func=render.timespan,
    )
    yield Result(
        state=State.OK,
        summary=f"Backup time: {time.strftime('%c', time.localtime(timestamp))}",
    )
    # 3. check total size of directory above configured threshold
    yield from check_levels(
        total_size,
        "total_size",
        params.get("total_size"),
        infoname="Total size",
        human_readable_func=render.disksize,
    )


agent_section_plesk_backups = AgentSection(
    name="plesk_backups",
    parse_function=parse_plesk_backups,
)


check_plugin_plesk_backups = CheckPlugin(
    name="plesk_backups",
    service_name="Plesk Backup %s",
    discovery_function=discover_plesk_backups,
    check_function=check_plesk_backups,
    check_ruleset_name="plesk_backups",
    check_default_parameters={
        "backup_age": None,
        "total_size": None,
        "no_backup_configured_state": 1,
        "no_backup_found_state": 1,
    },
)
