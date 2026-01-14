#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, SNMPTree, startswith
from cmk.base.check_legacy_includes.raritan import raritan_pdu_plug_state

check_info = {}


def parse_raritan_pdu_plugs(string_table):
    parsed = {}

    for outlet_label, outlet_name, outlet_state in string_table:
        state = raritan_pdu_plug_state.get(outlet_state, "unknown")
        parsed[outlet_label] = {"state": state, "outlet_name": outlet_name}

    return parsed


def discover_raritan_pdu_plugs(parsed):
    for key, value in parsed.items():
        if (state := value["state"]) != "unknown":
            yield key, {"discovered_state": state}


def check_raritan_pdu_plugs(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    if outlet_name := data.get("outlet_name"):
        yield 0, outlet_name

    state = data["state"]
    expected_state = params["required_state"] or params["discovered_state"]

    if state != expected_state:
        yield (2, f"Status: {state} (expected: {expected_state})")
    else:
        yield 0, "Status: %s" % state


check_info["raritan_pdu_plugs"] = LegacyCheckDefinition(
    name="raritan_pdu_plugs",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.6"),
        any_of(
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX2-2"),
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX3"),
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=["3.5.3.1.2", "3.5.3.1.3", "4.1.2.1.3"],
    ),
    parse_function=parse_raritan_pdu_plugs,
    service_name="Plug %s",
    discovery_function=discover_raritan_pdu_plugs,
    check_function=check_raritan_pdu_plugs,
    check_ruleset_name="plugs",
    check_default_parameters={"required_state": None},
)
