#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Iterable
from typing import NamedTuple

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree
from cmk.plugins.lib.fireeye import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.11.5.1.5.0 456.180 --> FE-FIREEYE-MIB::feSecurityContentVersion.0
# .1.3.6.1.4.1.25597.11.5.1.6.0 1 --> FE-FIREEYE-MIB::feLastContentUpdatePassed.0
# .1.3.6.1.4.1.25597.11.5.1.7.0 2016/02/26 15:42:06 --> FE-FIREEYE-MIB::feLastContentUpdateTime.0


class SecurityContent(NamedTuple):
    version: str
    update_status: str | None
    update_time_str: str
    update_time_seconds: float | None


def parse_fireeye_content(string_table):
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


def discover_fireeye_content(section: SecurityContent) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_fireeye_content(_no_item, params, parsed):
    if parsed.update_status != "OK":
        yield 1, "Update: failed"

    yield 0, "Last update: %s" % parsed.update_time_str

    if parsed.update_time_seconds is None:
        yield 0, "update has never completed"
    else:
        yield check_levels(
            time.time() - parsed.update_time_seconds,
            None,
            params.get("update_time_levels"),
            human_readable_func=render.timespan,
            infoname="Age",
        )

    yield 0, "Security version: %s" % parsed.version


check_info["fireeye_content"] = LegacyCheckDefinition(
    name="fireeye_content",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1",
        oids=["5", "6", "7"],
    ),
    parse_function=parse_fireeye_content,
    service_name="Security content",
    discovery_function=discover_fireeye_content,
    check_function=check_fireeye_content,
    check_ruleset_name="fireeye_content",
)
