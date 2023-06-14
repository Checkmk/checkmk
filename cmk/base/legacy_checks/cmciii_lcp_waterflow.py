#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="no-untyped-def"

from typing import Iterable, NamedTuple, Optional

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith


class WaterflowReading(NamedTuple):
    name: str
    status: str
    unit: str
    flow: float
    minflow: float
    maxflow: float


Section = Optional[WaterflowReading]


def parse_cmciii_lcp_waterflow(info) -> Section:
    if not info:
        return None

    # We have a list of values where no item has a fixed index. We
    # try to detect the starting index for the needed values now.
    iter_info = iter(info[0])
    name = None
    for line in iter_info:
        if "Waterflow" in line:
            name = line
            break

    if name is None:
        return None

    flow, unit = next(iter_info).split(" ", 1)
    maxflow = next(iter_info).split(" ", 1)[0]
    minflow = next(iter_info).split(" ", 1)[0]
    status = next(iter_info)

    return WaterflowReading(
        name=name,
        status=status,
        unit=unit,
        flow=float(flow),
        minflow=float(minflow),
        maxflow=float(maxflow),
    )


def inventory_cmciii_lcp_waterflow(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_cmciii_lcp_waterflow(item, params, section: Section):
    if not section:
        return None

    sym = ""
    state = 0
    if section.status != "OK":
        state = 2
        sym = "(!!)"
    elif section.flow < section.minflow or section.flow > section.maxflow:
        state = 1
        sym = "(!)"

    info_text = "%s Status: %s Flow: %.1f%s, MinFlow: %.1f, MaxFLow: %.1f" % (
        section.name,
        section.status,
        section.flow,
        sym,
        section.minflow,
        section.maxflow,
    )

    perfdata = [
        (
            "flow",
            str(section.flow) + section.unit,
            str(section.minflow) + ":" + str(section.maxflow),
            0,
            0,
        )
    ]

    return state, info_text, perfdata


check_info["cmciii_lcp_waterflow"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Rittal LCP"),
    parse_function=parse_cmciii_lcp_waterflow,
    check_function=check_cmciii_lcp_waterflow,
    discovery_function=inventory_cmciii_lcp_waterflow,
    service_name="LCP Fanunit WATER FLOW",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2606.7.4.2.2.1.10.2",
        oids=["74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85", "86", "87"],
    ),
)
