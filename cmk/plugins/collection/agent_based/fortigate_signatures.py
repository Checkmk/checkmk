#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.12356.101.4.2.1.0 27.00768(2015-09-01 15:10)
# .1.3.6.1.4.1.12356.101.4.2.2.0 6.00689(2015-09-01 00:15)

# signature ages (defaults are 1/2 days)

import re
import time
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.fortinet import DETECT_FORTIGATE

Section = list[tuple[str, str, str | None, float | None]]


def parse_fortigate_signatures(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    def parse_version(ver):
        # sample: 27.00768(2015-09-01 15:10)
        ver_regex = re.compile(r"([0-9.]*)\(([0-9-: ]*)\)")
        match = ver_regex.match(ver)
        if match is None:
            return None, None
        # what timezone is this in?
        t = time.strptime(match.group(2), "%Y-%m-%d %H:%M")
        ts = time.mktime(t)
        return match.group(1), time.time() - ts

    parsed = []
    for (key, title), value in zip(
        [
            ("av_age", "AV"),
            ("ips_age", "IPS"),
            ("av_ext_age", "AV extended"),
            ("ips_ext_age", "IPS extended"),
        ],
        string_table[0],
    ):
        version, age = parse_version(value)
        parsed.append((key, title, version, age))
    return parsed


def discover_fortigate_signatures(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_fortigate_signatures(params: dict[str, Any], section: Section) -> CheckResult:
    for key, title, version, age in section:
        if age is None:
            continue
        # TODO: remove this levels migration logic by migrating the check parameters to formspecs
        levels_upper: LevelsT[int] | None = None
        if key in params:
            _params = params[key]
            if _params[0] is None:
                levels_upper = ("no_levels", None)
            else:
                levels_upper = ("fixed", _params)

        yield from check_levels(
            age,
            levels_upper=levels_upper,
            render_func=render.timespan,
            label=f"[{version}] {title} age",
        )


snmp_section_fortigate_signatures = SimpleSNMPSection(
    name="fortigate_signatures",
    parse_function=parse_fortigate_signatures,
    detect=DETECT_FORTIGATE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.4.2",
        oids=["1", "2", "3", "4"],
    ),
)


check_plugin_fortigate_signatures = CheckPlugin(
    name="fortigate_signatures",
    service_name="Signatures",
    discovery_function=discover_fortigate_signatures,
    check_function=check_fortigate_signatures,
    check_ruleset_name="fortinet_signatures",
    check_default_parameters={
        "av_age": (86400, 172800),
        "ips_age": (86400, 172800),
    },
)
