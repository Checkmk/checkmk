#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.plugins.collection.agent_based.apc_rackpdu_power import Section

check_info = {}


def discover_apc_rackpdu_power(section: Section) -> LegacyDiscoveryResult:
    yield from ((item, {}) for item in section)


def check_apc_rackpdu_power(
    item: str, params: Mapping[str, Any], section: Section
) -> LegacyCheckResult:
    if (power := section.get(item)) is None:
        return

    if (entry := power.get("current")) is not None:
        value, state_info = entry
        yield check_levels(
            value,
            "current",
            params=params.get("current"),
            human_readable_func=lambda v: f"{v:.1f} A",
            infoname="Current",
        )
        yield state_info

    if (value_power := power.get("power")) is not None:
        yield check_levels(
            value_power,
            "power",
            params.get("power"),
            human_readable_func=lambda v: f"{v:.1f} W",
            infoname="Power",
        )


check_info["apc_rackpdu_power"] = LegacyCheckDefinition(
    name="apc_rackpdu_power",
    service_name="PDU %s",
    discovery_function=discover_apc_rackpdu_power,
    check_function=check_apc_rackpdu_power,
    # todo: use dedicated ruleset. Most of what can be confgured in the ruleset has no effect here.
    check_ruleset_name="el_inphase",
)
