#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import NamedTuple

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fireeye.lib import DETECT

# .1.3.6.1.4.1.25597.11.5.1.5.0 456.180 --> FE-FIREEYE-MIB::feSecurityContentVersion.0
# .1.3.6.1.4.1.25597.11.5.1.6.0 1 --> FE-FIREEYE-MIB::feLastContentUpdatePassed.0
# .1.3.6.1.4.1.25597.11.5.1.7.0 2016/02/26 15:42:06 --> FE-FIREEYE-MIB::feLastContentUpdateTime.0


class SecurityContent(NamedTuple):
    version: str
    update_status: str | None
    update_time_str: str
    update_time_seconds: float | None


def parse_fireeye_content(string_table: StringTable) -> SecurityContent | None:
    if not string_table:
        return None

    security_content_status_map = {
        "1": "OK",
        "0": "failed",
    }

    version, update_status_raw, update_time_str = string_table[0]
    update_status = security_content_status_map.get(update_status_raw)

    # If content update has never completed, last_update_time contains no valid timestamp
    # In that case, we just skip the output
    try:
        update_time_seconds = time.mktime(time.strptime(update_time_str, "%Y/%m/%d %H:%M:%S"))
    except ValueError:
        update_time_seconds = None

    return SecurityContent(version, update_status, update_time_str, update_time_seconds)


def discover_fireeye_content(section: SecurityContent) -> DiscoveryResult:
    yield Service()


def check_fireeye_content(
    params: Mapping[str, tuple[float, float]], section: SecurityContent
) -> CheckResult:
    if section.update_status != "OK":
        yield Result(state=State.WARN, summary="Update: failed")

    yield Result(state=State.OK, summary=f"Last update: {section.update_time_str}")

    if section.update_time_seconds is None:
        yield Result(state=State.OK, summary="update has never completed")
    else:
        yield from check_levels(
            time.time() - section.update_time_seconds,
            levels_upper=("fixed", levels)
            if (levels := params.get("update_time_levels"))
            else ("no_levels", None),
            render_func=render.timespan,
            label="Age",
        )

    yield Result(state=State.OK, summary=f"Security version: {section.version}")


snmp_section_fireeye_content = SimpleSNMPSection(
    name="fireeye_content",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1",
        oids=["5", "6", "7"],
    ),
    parse_function=parse_fireeye_content,
)


check_plugin_fireeye_content = CheckPlugin(
    name="fireeye_content",
    service_name="Security content",
    discovery_function=discover_fireeye_content,
    check_function=check_fireeye_content,
    check_ruleset_name="fireeye_content",
    check_default_parameters={},
)
