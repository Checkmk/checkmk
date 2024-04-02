#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import any_of, contains, SNMPTree, StringTable

# For Hitachi Unified Storage (HUS) devices which support the USPMIB
# This devices has two units: Disk Controller (DKC) and Disk Unit (DKC)

# Example output from DKC:
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.1 470849
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.2 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.3 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.4 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.5 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.6 5
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.7 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.8 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.9 1

# Example output from DKU:
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.1 470849
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.2 1
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.3 4
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.4 3
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.5 1


@dataclass(frozen=True)
class PropertyState:
    label: str
    state: int
    description: str


Section = Mapping[str, Sequence[PropertyState]]


_DETECT_HUS = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "hm700"),
    contains(".1.3.6.1.2.1.1.1.0", "hm800"),
    contains(".1.3.6.1.2.1.1.1.0", "hm850"),
    contains(".1.3.6.1.2.1.1.1.0", "hm900"),
)


_HUS_MAP_STATES = {
    "0": (3, "unknown"),
    "1": (0, "no error"),
    "2": (2, "acute"),
    "3": (2, "serious"),
    "4": (1, "moderate"),
    "5": (1, "service"),
}


def parse_hitachi_hus_dkc(string_table: StringTable) -> Section:
    labels = (
        "Processor",
        "Internal Bus",
        "Cache",
        "Shared Memory",
        "Power Supply",
        "Battery",
        "Fan",
        "Environment",
    )

    return {
        item: tuple(
            PropertyState(l, *_HUS_MAP_STATES[v]) for l, v in zip(labels, rest, strict=True)
        )
        for item, *rest in string_table
    }


def parse_hitachi_hus_dku(string_table: StringTable) -> Section:
    labels = ("Power Supply", "Fan", "Environment", "Drive")

    return {
        item: tuple(
            PropertyState(l, *_HUS_MAP_STATES[v]) for l, v in zip(labels, rest, strict=True)
        )
        for item, *rest in string_table
    }


def inventory_hitachi_hus(section):
    for item in section:
        yield item, None


def check_hitachi_hus(item, _no_params, section):

    if (data := section.get(item)) is None:
        return

    for prop in data:
        yield prop.state, f"{prop.label}: {prop.description}"


check_info["hitachi_hus_dkc"] = LegacyCheckDefinition(
    parse_function=parse_hitachi_hus_dkc,
    detect=_DETECT_HUS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.116.5.11.4.1.1.6.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ),
    service_name="HUS DKC Chassis %s",
    discovery_function=inventory_hitachi_hus,
    check_function=check_hitachi_hus,
)


check_info["hitachi_hus_dku"] = LegacyCheckDefinition(
    parse_function=parse_hitachi_hus_dku,
    detect=_DETECT_HUS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.116.5.11.4.1.1.7.1",
        oids=["1", "2", "3", "4", "5"],
    ),
    service_name="HUS DKU Chassis %s",
    discovery_function=inventory_hitachi_hus,
    check_function=check_hitachi_hus,
)
