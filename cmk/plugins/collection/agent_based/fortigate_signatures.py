#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.12356.101.4.2.1.0 27.00768(2015-09-01 15:10)
# .1.3.6.1.4.1.12356.101.4.2.2.0 6.00689(2015-09-01 00:15)

# signature ages (defaults are 1/2 days)

import re
import time
from collections.abc import Mapping
from typing import Final, Literal, NamedTuple, NotRequired, TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.fortinet import DETECT_FORTIGATE

FortigateSignatureKey = Literal["av_age", "ips_age", "av_ext_age", "ips_ext_age"]


class FortigateSignatureEntry(NamedTuple):
    version: str | None
    age: float | None


FORTIGATE_KEY_TO_TITLE_MAP: Final[Mapping[FortigateSignatureKey, str]] = {
    "av_age": "AV",
    "ips_age": "IPS",
    "av_ext_age": "AV Extended",
    "ips_ext_age": "IPS Extended",
}

Section = dict[FortigateSignatureKey, FortigateSignatureEntry]

Levels = tuple[int, int] | tuple[None, None]


class FortigateSignaturesParams(TypedDict):
    av_age: NotRequired[Levels]
    ips_age: NotRequired[Levels]
    av_ext_age: NotRequired[Levels]
    ips_ext_age: NotRequired[Levels]


def _parse_version(version_string: str) -> tuple[str, float] | tuple[None, None]:
    # sample: 27.00768(2015-09-01 15:10)
    version_regex = re.compile(r"([0-9.]*)\(([0-9-: ]*)\)")
    match = version_regex.match(version_string)
    if match is None:
        return None, None
    # what timezone is this in?
    t = time.strptime(match.group(2), "%Y-%m-%d %H:%M")
    ts = time.mktime(t)
    return match.group(1), time.time() - ts


def parse_fortigate_signatures(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    return {
        key: FortigateSignatureEntry(*_parse_version(value))
        for key, value in zip(FORTIGATE_KEY_TO_TITLE_MAP.keys(), string_table[0])
    }


def discover_fortigate_signatures(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_fortigate_signatures(params: FortigateSignaturesParams, section: Section) -> CheckResult:
    for key, entry in section.items():
        if entry.age is None:
            continue
        if entry.age < 0:
            yield Result(
                state=State.OK,
                summary=(
                    f"The age of the signature appears to be {render.time_offset(entry.age)}. "
                    "Since this is in the future you should check your system time."
                ),
            )
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
            entry.age,
            levels_upper=levels_upper,
            render_func=render.timespan,
            label=f"[{entry.version}] {FORTIGATE_KEY_TO_TITLE_MAP[key]} age",
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
    check_default_parameters=FortigateSignaturesParams(
        av_age=(86400, 172800),
        ips_age=(86400, 172800),
    ),
)
