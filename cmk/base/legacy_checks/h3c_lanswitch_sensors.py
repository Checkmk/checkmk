#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.base.check_api import contains
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree

Section = Mapping[str, str]


def parse_h3c_lanswitch_sensors(string_table: list[list[list[str]]]) -> Section:
    return {
        h3c_lanswitch_genitem(device_class, item): state
        for device_class, info in zip(("Fan", "Powersupply"), string_table)
        for item, state in info
    }


def inventory_h3c_lanswitch_sensors(section: Section) -> list[tuple[str, dict]]:
    return [(item, {}) for item, state in section.items() if state in ["1", "2"]]


def check_h3c_lanswitch_sensors(
    item: str, _no_params: object, section: Section
) -> Iterable[tuple[int, str]]:
    if (status := section.get(item)) is None:
        return

    # the values are:   active     (1), deactive   (2), not-install  (3), unsupport    (4)
    match status:
        case "2":
            yield 2, "Sensor %s status is %s" % (item, status)
        case "1":
            yield 0, "Sensor %s status is %s" % (item, status)
        case _:
            yield 1, "Sensor % status is %s" % (item, status)


check_info["h3c_lanswitch_sensors"] = {
    "detect": contains(".1.3.6.1.2.1.1.1.0", "3com s"),
    "parse_function": parse_h3c_lanswitch_sensors,
    "discovery_function": inventory_h3c_lanswitch_sensors,
    "check_function": check_h3c_lanswitch_sensors,
    "service_name": "%s",
    "fetch": [
        SNMPTree(
            base=".1.3.6.1.4.1.43.45.1.2.23.1.9.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.43.45.1.2.23.1.9.1.2.1",
            oids=[OIDEnd(), "2"],
        ),
    ],
}


def h3c_lanswitch_genitem(device_class: str, id_: str) -> str:
    unitid = int(id_) // 65536
    num = int(id_) % 65536
    return "Unit %d %s %d" % (unitid, device_class, num)
