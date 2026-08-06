#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from dataclasses import dataclass
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


@dataclass(frozen=True, kw_only=True)
class LicenseUsage:
    used: int
    total: int

    def __post_init__(self) -> None:
        if self.used < 0 or self.total < 0:
            raise ValueError("Negative values are not allowed.")

    @property
    def utilization(self) -> float | None:
        return (100.0 * self.used) / self.total if self.total else None


def parse_innovaphone_licenses(string_table: StringTable) -> LicenseUsage | None:
    match string_table:
        case [[str(total), str(used)]] if total.isdigit() and used.isdigit():
            try:
                return LicenseUsage(used=int(used), total=int(total))
            except ValueError:
                return None
        case _:
            return None


def discover_innovaphone_licenses(section: LicenseUsage) -> DiscoveryResult:
    yield Service()


def check_innovaphone_licenses(params: Mapping[str, Any], section: LicenseUsage) -> CheckResult:
    perc_used = section.utilization
    warn, crit = params["levels"]
    utilization_message = f" ({perc_used:.0f}%)" if perc_used is not None else ""
    message = f"Used {section.used}/{section.total} Licences{utilization_message}"
    levels = f"Warning/ Critical at ({warn}/{crit})"
    if perc_used is None:
        yield Result(state=State.UNKNOWN, summary=message)
    elif perc_used > crit:
        yield Result(state=State.CRIT, summary=message + levels)
    elif perc_used > warn:
        yield Result(state=State.WARN, summary=message + levels)
    else:
        yield Result(state=State.OK, summary=message)
    yield Metric("licenses", section.used, boundaries=(0, section.total))


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
