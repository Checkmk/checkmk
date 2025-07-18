#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.plugins.lib.netgear import DETECT_NETGEAR

check_info = {}

# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.0 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.0
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.1 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.1
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.2 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.2
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.3 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.3
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.4 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.4
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.5 1 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.5
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.0 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.0
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.1 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.1
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.2 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.2
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.3 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.3
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.4 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.4
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.5 1 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.5
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.0 3950 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.0
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.1 3700 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.1
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.2 3600 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.2
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.3 3400 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.3
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.4 0 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.4
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.5 0 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.5
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.0 3650 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.0
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.1 3400 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.1
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.2 3300 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.2
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.3 3500 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.3
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.4 0 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.4
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.5 0 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.5

# Just assumed


def netgear_map_state_txt_to_int(state_nr, version):
    map_state_txt_to_int = {
        "operational": 0,
        "failed": 2,
        "powering": 0,
        "not powering": 1,
        "not present": 1,
        "no power": 2,
        "incompatible": 2,
    }

    if version.startswith("8."):
        map_states = {
            "1": "operational",
            "2": "failed",
            "3": "powering",
            "4": "not powering",
            "5": "not present",
        }
    elif version.startswith("10."):
        map_states = {
            "1": "notpresent",
            "2": "operational",
            "3": "failed",
            "4": "powering",
            "5": "no power",
            "6": "not powering",
            "7": "incompatible",
        }
    else:
        map_states = {
            "1": "not present",
            "2": "operational",
            "3": "failed",
        }

    state_txt = map_states.get(state_nr, "unknown(%s)" % state_nr)
    return map_state_txt_to_int.get(state_txt, 3), state_txt


def parse_netgear_fans(string_table):
    versioninfo, sensorinfo = string_table
    if versioninfo == []:
        parsed = {"__fans__": {}}
    else:
        parsed = {
            "__version__": versioninfo[0][0],
            "__fans__": {},
        }
    for oid_end, sstate, reading_str in sensorinfo:
        parsed["__fans__"].setdefault(
            "%s" % oid_end.replace(".", "/"),
            {
                "state": sstate,
                "reading_str": reading_str,
            },
        )
    return parsed


def inventory_netgear_fans(parsed):
    for sensorname, sensorinfo in parsed["__fans__"].items():
        state = sensorinfo["state"]
        if state != "1" and not (state == "2" and sensorinfo["reading_str"] in ["0"]):
            yield sensorname, {}


def check_netgear_fans(item, params, parsed):
    data = parsed["__fans__"].get(item)
    if data is None:
        return

    reading_str = data["reading_str"]
    if reading_str != "Not Supported":
        yield check_fan(int(data["reading_str"]), params)
    state, state_readable = netgear_map_state_txt_to_int(
        data["state"], parsed.get("__version__", "")
    )
    yield state, "Status: %s" % state_readable


check_info["netgear_fans"] = LegacyCheckDefinition(
    name="netgear_fans",
    detect=DETECT_NETGEAR,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.4526.10.1.1.1",
            oids=["13"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.4526.10.43.1.6.1",
            oids=[OIDEnd(), "3", "4"],
        ),
    ],
    parse_function=parse_netgear_fans,
    service_name="Fan %s",
    discovery_function=inventory_netgear_fans,
    check_function=check_netgear_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (1500, 1200),
    },
)
