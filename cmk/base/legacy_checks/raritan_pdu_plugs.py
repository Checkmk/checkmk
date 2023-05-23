#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.raritan import raritan_map_state
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import all_of, any_of, SNMPTree, startswith


def parse_raritan_pdu_plugs(info):
    parsed = {}

    for outlet_label, outlet_name, outlet_state in info:
        parsed[outlet_label] = {
            "state": raritan_map_state.get(outlet_state, (3, "unknown")),
            "outlet_name": outlet_name,
        }
    return parsed


def inventory_raritan_pdu_plugs(parsed):
    for key, value in parsed.items():
        yield key, {"discovered_state": value["state"][1]}


@get_parsed_item_data
def check_raritan_pdu_plugs(_no_item, params, data):
    if data.get("outlet_name"):
        yield 0, data["outlet_name"]

    state, state_info = data["state"]
    yield state, "Status: %s" % state_info

    required_state = params.get("required_state", params["discovered_state"])
    if state_info != required_state:
        yield 2, "Expected: %s" % required_state


check_info["raritan_pdu_plugs"] = LegacyCheckDefinition(
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.6"),
        any_of(
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX2-2"),
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX3"),
        ),
    ),
    discovery_function=inventory_raritan_pdu_plugs,
    parse_function=parse_raritan_pdu_plugs,
    check_function=check_raritan_pdu_plugs,
    service_name="Plug %s",
    check_ruleset_name="plugs",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=["3.5.3.1.2", "3.5.3.1.3", "4.1.2.1.3"],
    ),
)
