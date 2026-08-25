#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="unreachable"

import contextlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)

from .liboracle import Error, Ok, oracle_handle_ora_errors, Parsed

# <<<oracle_logswitches>>>
# pengt  15
# hirni  22

type Section = Mapping[str, Parsed[int]]


def parse_oracle_logswitches(string_table: StringTable) -> Section:
    counts: dict[str, int] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match oracle_handle_ora_errors(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                if len(line) == 2:
                    with contextlib.suppress(ValueError):
                        counts.setdefault(line[0], int(line[1]))

    parsed: dict[str, Parsed[int]] = {
        sid: Ok(count) for sid, count in counts.items() if sid not in errors
    }
    for sid, message in errors.items():
        parsed[sid] = Error(message)
    return parsed


def discover_oracle_logswitches(section: Section) -> DiscoveryResult:
    yield from (Service(item=sid) for sid, result in section.items() if isinstance(result, Ok))


def check_oracle_logswitches(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if isinstance(params, tuple):
        params = {
            "levels": (params[2], params[3]),
            "levels_lower": (params[0], params[1]),
        }

    match section.get(item):
        case None:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("Login into database failed")
        case Error(message):
            yield Result(state=State.UNKNOWN, summary=message)
        case Ok(logswitches):
            lowarn, locrit = params["levels_lower"]
            warn, crit = params["levels"]
            yield from check_levels(
                logswitches,
                metric_name="logswitches",
                levels_lower=("fixed", (lowarn, locrit)),
                levels_upper=("fixed", (warn, crit)),
                render_func=str,
                label="Log switches in the last 60 minutes",
            )


agent_section_oracle_logswitches = AgentSection(
    name="oracle_logswitches",
    parse_function=parse_oracle_logswitches,
)


check_plugin_oracle_logswitches = CheckPlugin(
    name="oracle_logswitches",
    service_name="ORA %s Logswitches",
    discovery_function=discover_oracle_logswitches,
    check_function=check_oracle_logswitches,
    check_ruleset_name="oracle_logswitches",
    check_default_parameters={
        "levels": (50, 100),
        "levels_lower": (-1, -1),
    },
)
