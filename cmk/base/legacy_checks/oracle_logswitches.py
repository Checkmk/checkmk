#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any, assert_never

from cmk.base.check_legacy_includes.oracle import (
    oracle_handle_ora_errors,
    oracle_handle_ora_errors_discovery,
)

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    StringTable,
)

# <<<oracle_logswitches>>>
# pengt  15
# hirni  22


def inventory_oracle_logswitches(section: StringTable) -> DiscoveryResult:
    oracle_handle_ora_errors_discovery(section)
    yield from [Service(item=line[0]) for line in section if len(line) == 2]


def check_oracle_logswitches(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    if isinstance(params, tuple):
        params = {
            "levels": (params[2], params[3]),
            "levels_lower": (params[0], params[1]),
        }

    for line in section:
        if line[0] == item:
            err = oracle_handle_ora_errors(line)
            if err is False:
                continue
            elif isinstance(err, Result):
                yield err
            elif err is None:
                pass
            else:
                assert_never(err)

            if len(line) != 2:
                continue

            lowarn, locrit = params["levels_lower"]
            warn, crit = params["levels"]
            logswitches = int(line[1])
            yield from check_levels(
                logswitches,
                metric_name="logswitches",
                levels_lower=("fixed", (lowarn, locrit)),
                levels_upper=("fixed", (warn, crit)),
                render_func=str,
                label="Log switches in the last 60 minutes",
            )
            return

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


def parse_oracle_logswitches(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_logswitches = AgentSection(
    name="oracle_logswitches",
    parse_function=parse_oracle_logswitches,
)


check_plugin_oracle_logswitches = CheckPlugin(
    name="oracle_logswitches",
    service_name="ORA %s Logswitches",
    discovery_function=inventory_oracle_logswitches,
    check_function=check_oracle_logswitches,
    check_ruleset_name="oracle_logswitches",
    check_default_parameters={
        "levels": (50, 100),
        "levels_lower": (-1, -1),
    },
)
