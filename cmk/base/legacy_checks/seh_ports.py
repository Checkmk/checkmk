#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import get_parsed_item_data, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, OIDEnd, SNMPTree


def parse_seh_ports(info):
    parsed = {}
    for oid_end, tag, status, port_number in info[0]:
        oid_index = oid_end.split(".")[0]
        if tag != "":
            parsed.setdefault(oid_index, {}).update(tag=tag)
        if port_number != "0":
            parsed.setdefault(port_number, {}).update(status=status)
    return parsed


def inventory_seh_ports(parsed):
    for key, port in parsed.items():
        yield key, {"status_at_discovery": port.get("status")}


@get_parsed_item_data
def check_seh_ports(item, params, data):
    for key in ("tag", "status"):
        if key in data:
            yield 0, "%s: %s" % (key.title(), data[key])

    if params.get("status_at_discovery") != data.get("status"):
        yield 1, "Status during discovery: %s" % (params.get("status_at_discovery") or "unknown")


check_info["seh_ports"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1229.1.1"),
    parse_function=parse_seh_ports,
    discovery_function=inventory_seh_ports,
    check_function=check_seh_ports,
    service_name="Port %s",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1229.2.50.2.1",
            oids=[OIDEnd(), "10", "26", "27"],
        )
    ],
)
