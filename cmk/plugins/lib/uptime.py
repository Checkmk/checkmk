#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SNMPTree,
    State,
)


class Section(NamedTuple):
    uptime_sec: float | None
    message: str | None


UPTIME_TREE = SNMPTree(
    base=".1.3.6.1.2.1",
    oids=[
        # On Linux appliances: .1.3.6.1.2.1.1.3.0    means uptime of snmpd
        #                      .1.3.6.1.2.1.25.1.1.0 means system uptime
        "1.3",  # DISMAN-EVENT-MIB::sysUpTime
        "25.1.1",  # HOST-RESOURCES-MIB::hrSystemUptime
    ],
)


def discover(section: Section) -> DiscoveryResult:
    if section.uptime_sec:
        yield Service()


def check(params: Mapping[str, Any], section: Section) -> CheckResult:
    if section.message:
        yield Result(state=State.UNKNOWN, summary=section.message)

    if section.uptime_sec is None:
        return

    up_date = render.datetime(time.time() - section.uptime_sec)
    yield Result(state=State.OK, summary=f"Up since {up_date}")

    yield from check_levels(
        section.uptime_sec,
        levels_upper=params.get("max"),
        levels_lower=params.get("min"),
        metric_name="uptime",
        render_func=render.timespan,
        label="Uptime",
    )
