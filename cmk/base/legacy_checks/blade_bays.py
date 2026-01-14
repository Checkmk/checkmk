#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.plugins.blade.agent_based.detection import DETECT_BLADE

check_info = {}

# mypy: disable-error-code="var-annotated"


def parse_blade_bays(string_table):
    map_states = {
        "0": (0, "standby"),
        "1": (0, "on"),
        "2": (1, "not present"),
        "3": (1, "switched off"),
        "255": (2, "not applicable"),
    }

    parsed = {}
    for power_domain, block in zip((1, 2), string_table):
        for oid, name, state, ty, identifier, power_str, power_max_str in block:
            itemname = "PD%d %s" % (power_domain, name)
            if itemname in parsed:
                itemname = f"{itemname} {oid}"

            try:
                power = int(power_str.rstrip("W"))
                power_max = int(power_max_str.rstrip("W"))
            except ValueError:
                power = 0

            parsed.setdefault(
                itemname,
                {
                    "type": ty.split("(")[0],
                    "id": identifier,
                    "power_max": power_max,
                    "device_state": map_states.get(state, (3, "unhandled[%s]" % state)),
                    "power": power,
                },
            )

    return parsed


def discover_blade_bays(parsed):
    for entry, attrs in parsed.items():
        if attrs["device_state"][1] in ["standby", "on"]:
            yield entry, {}


def check_blade_bays(item, params, parsed):
    if item not in parsed:
        yield 3, "No data for '%s' in SNMP info" % item
        return

    data = parsed[item]
    state, state_readable = data["device_state"]
    yield state, "Status: %s" % state_readable

    yield from check_elphase(item, params, parsed)

    data = parsed[item]
    yield (
        0,
        "Max. power: {} W, Type: {}, ID: {}".format(data["power_max"], data["type"], data["id"]),
    )


check_info["blade_bays"] = LegacyCheckDefinition(
    name="blade_bays",
    detect=DETECT_BLADE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2.3.51.2.2.10.2.1.1",
            oids=[OIDEnd(), "5", "6", "2", "1", "7", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2.3.51.2.2.10.3.1.1",
            oids=[OIDEnd(), "5", "6", "2", "1", "7", "8"],
        ),
    ],
    parse_function=parse_blade_bays,
    service_name="BAY %s",
    discovery_function=discover_blade_bays,
    check_function=check_blade_bays,
)
