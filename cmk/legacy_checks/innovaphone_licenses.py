#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def discover_innovaphone_licenses(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_innovaphone_licenses(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if not section:
        return
    total, used = map(savefloat, section[0])
    perc_used = (100.0 * used) / total if total else None
    warn, crit = params["levels"]
    utilization_message = f" ({perc_used:.0f}%)" if perc_used is not None else ""
    message = f"Used {used:.0f}/{total:.0f} Licences{utilization_message}"
    levels = f"Warning/ Critical at ({warn}/{crit})"
    if perc_used is None:
        yield Result(state=State.UNKNOWN, summary=message)
    elif perc_used > crit:
        yield Result(state=State.CRIT, summary=message + levels)
    elif perc_used > warn:
        yield Result(state=State.WARN, summary=message + levels)
    else:
        yield Result(state=State.OK, summary=message)
    yield Metric("licenses", used, boundaries=(0, total))


def parse_innovaphone_licenses(string_table: StringTable) -> StringTable:
    return string_table


agent_section_innovaphone_licenses = AgentSection(
    name="innovaphone_licenses",
    parse_function=parse_innovaphone_licenses,
)


check_plugin_innovaphone_licenses = CheckPlugin(
    name="innovaphone_licenses",
    service_name="Licenses",
    discovery_function=discover_innovaphone_licenses,
    check_function=check_innovaphone_licenses,
    check_default_parameters={
        "levels": (90.0, 95.0),
    },
)
