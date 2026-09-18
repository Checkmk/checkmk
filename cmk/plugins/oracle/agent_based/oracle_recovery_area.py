#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# <<<oracle_recovery_area>>>
# TUX12C 0 4800 19 0

# Columns:
# ORACLE_SID used_pct size used reclaimable


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    InventoryPlugin,
    InventoryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)

from .liboracle import Error, Ok, oracle_handle_ora_errors, Parsed

type _RecoveryRows = list[Sequence[str]]
type Section = Mapping[str, Parsed[_RecoveryRows]]


def parse_oracle_recovery_area(string_table: StringTable) -> Section:
    rows_by_sid: dict[str, _RecoveryRows] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match oracle_handle_ora_errors(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                rows_by_sid.setdefault(line[0], []).append(line)

    parsed: dict[str, Parsed[_RecoveryRows]] = {
        sid: Ok(rows) for sid, rows in rows_by_sid.items() if sid not in errors
    }
    for sid, message in errors.items():
        parsed[sid] = Error(message)
    return parsed


def discover_oracle_recovery_area(section: Section) -> DiscoveryResult:
    for sid, result in section.items():
        if isinstance(result, Ok):
            yield from (Service(item=sid) for _line in result.value)


def check_oracle_recovery_area(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    match section.get(item):
        case None:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("Login into database failed")
        case Error(message):
            yield Result(state=State.UNKNOWN, summary=message)
        case Ok(rows):
            yield from _check_recovery_area(params, rows)


def _check_recovery_area(params: Mapping[str, Any], rows: _RecoveryRows) -> CheckResult:
    for line in rows:
        if len(line) < 5:
            continue
        size_mb, used_mb, reclaimable_mb = map(int, line[2:5])
        perc_used = 0.0 if size_mb == 0 else float(used_mb - reclaimable_mb) / size_mb * 100

        warn, crit = params["levels"]
        warn_mb = size_mb * warn / 100
        crit_mb = size_mb * crit / 100

        if perc_used >= crit:
            state = State.CRIT
        elif perc_used >= warn:
            state = State.WARN
        else:
            state = State.OK

        mb = 1024 * 1024
        yield Result(
            state=state,
            summary="%s out of %s used (%.1f%%, warn/crit at %s%%/%s%%), %s reclaimable"
            % (
                render.bytes(used_mb * mb),
                render.bytes(size_mb * mb),
                perc_used,
                warn,
                crit,
                render.bytes(reclaimable_mb * mb),
            ),
        )
        yield Metric("used", used_mb, levels=(warn_mb, crit_mb), boundaries=(0, size_mb))
        yield Metric("reclaimable", reclaimable_mb)
        return

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


agent_section_oracle_recovery_area = AgentSection(
    name="oracle_recovery_area",
    parse_function=parse_oracle_recovery_area,
)


check_plugin_oracle_recovery_area = CheckPlugin(
    name="oracle_recovery_area",
    service_name="ORA %s Recovery Area",
    discovery_function=discover_oracle_recovery_area,
    check_function=check_oracle_recovery_area,
    check_ruleset_name="oracle_recovery_area",
    check_default_parameters={
        "levels": (70.0, 90.0),
    },
)


def inventorize_oracle_recovery_area(section: Section) -> InventoryResult:
    for result in section.values():
        if not isinstance(result, Ok):
            continue
        for line in result.value:
            yield TableRow(
                path=["software", "applications", "oracle", "recovery_area"],
                key_columns={
                    "sid": line[0],
                },
                inventory_columns={
                    "flashback": line[-1],
                },
                status_columns={},
            )


inventory_plugin_oracle_recovery_area = InventoryPlugin(
    name="oracle_recovery_area",
    inventory_function=inventorize_oracle_recovery_area,
)
