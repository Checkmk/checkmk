#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping
from typing import Any, Final, Literal

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[int, float]]

#
# The ewon2005cd is a vpn that can also be used to expose data from a
# secondary device via snmp. Unfortunately there is no way to reliably
# identify that secondary device
#

# configuration for the tags used in Wagner OxyReduct devices
# for analog measures, "levels" is provided as upper and lower bounds (warn and crit each)
# for digital bitfields the "expected" bitmask is provided, that is: the bits we expect to see,
#  Anything that doesn't match this mask causes a crit status.
#  Note: bitmasks are specified most-significant-bit to least-significant bit
#  Some symbols have special meaning:
#    "?" - we don't care about this flag
#    "*" - add the flag to the infotext but don't derive a state from it
#    "+" - add the flag to the infotext if it is set but don't derive a state from it
# Also, we provide the names of flags for proper info texts.

_O2_MINIMUM: Final = {
    "name": "O2 minimum",
    "levels": (16, 17, 14, 13),
    "scale": 0.01,
    "unit": "%",
    "perfvar": "o2_percentage",
    "condition_flag": (1, 15),
}

_FLAGS_7_9: Final = {
    "flags": "?????000??00000*",
    "flag_names": [
        "",
        "",
        "",
        "",
        "",
        "luminous field",
        "optical alarm",
        "acoustic alarm",
        "",
        "",
        "warnings",
        "operation report",
        "shutdown",
        "incidents",
        "alarm",
        "O2 Sensor",
    ],
}

_OXYREDUCT_TAG_MAP: Final[Mapping[int, Mapping[str, Any]]] = {
    1: {"name": "alarms", "levels": (1, 2, -1, -1)},
    2: {"name": "incidents", "levels": (1, 2, -1, -1)},
    3: {"name": "shutdown messages", "levels": (1, 2, -1, -1)},
    4: {
        "flags": "00000????0000000",
        "flag_names": [
            "buzzer",
            "light test",
            "luminous field",
            "optical alarm",
            "accustic alarm",
            "",
            "",
            "",
            "",
            "warnings",
            "shutdown",
            "operation reports",
            "incident",
            "O2 high",
            "O2 low",
            "alarms",
        ],
    },
    5: {
        "flags": "00??????00**0101",
        "flag_names": [
            "recovery",
            "maintenance",
            "",
            "",
            "",
            "",
            "",
            "",
            "warnings",
            "incidents",
            "N2 to safe area",
            "N2 request from safe area",
            "N2 via outlet",
            "N2 via compressor",
            "N2-supply locked",
            "N2-supply open",
        ],
    },
    6: _O2_MINIMUM,
    7: _FLAGS_7_9,
    8: _O2_MINIMUM,
    9: _FLAGS_7_9,
    10: {
        "name": "O2 average",
        "levels_name": "o2_levels",
        "levels": (16, 17, 14, 13),
        "scale": 0.01,
        "unit": "%",
        "perfvar": "o2_percentage",
    },
    11: {"name": "O2 target", "scale": 0.01, "unit": "%"},
    12: {"name": "O2 for N2-in", "scale": 0.01, "unit": "%"},
    13: {"name": "O2 for N2-out", "scale": 0.01, "unit": "%"},
    14: {"name": "CO2 maximum", "levels": (1500, 2000, -1, -1), "unit": "ppm"},
    15: {
        "flags": "????++++????++++",
        "flag_names": [
            "",
            "",
            "",
            "",
            "air control shutdown",
            "air control closed",
            "air control open",
            "air control active",
            "",
            "",
            "",
            "",
            "valve shutdown",
            "valve closed",
            "valve open",
            "valve active",
        ],
    },
    16: {
        "flags": "????++++????++++",
        "flag_names": [
            "",
            "",
            "",
            "",
            "access shutdown",
            "access closed",
            "access open",
            "access active",
            "",
            "",
            "",
            "",
            "air circulation shutdown",
            "air circulation closed",
            "air circulation open",
            "air circulation active",
        ],
    },
    17: {
        "flags": "??00++++0?000001",
        "flag_names": [
            "O2 ref sensors working",
            "O2 ref sensors projected",
            "BMZ quick reduction",
            "key switch active",
            "mode BK3",
            "mode BK2",
            "mode BK1",
            "mode FB",
            "operation mode change",
            "",
            "warnings",
            "operation reports",
            "shutdown",
            "incidents",
            "alarm",
            "active",
        ],
    },
}


def parse_ewon(string_table: StringTable) -> Section:
    result: dict[str, dict[int, float]] = {}
    for tagid, value, name in string_table:
        result.setdefault(name, {})[int(tagid)] = float(value)
    return result


snmp_section_ewon = SimpleSNMPSection(
    name="ewon",
    parse_function=parse_ewon,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8284.2.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.8284.2.1.3.1.11.1",
        oids=[
            "2",  # tagCfgId
            "4",  # tagValue
            "16",  # undocumented name field
        ],
    ),
)


def _discovery_oxyreduct_names(section: Section) -> Iterable[str]:
    for name, area_info in section.items():
        tagids = area_info
        if min(tagids) < 10:
            yield name
        else:
            # for the "optional" rooms the lsb of the last bitmask says whether the room is used
            flags = int(area_info[max(tagids)])
            if flags % 2 == 1:
                yield name


def _to_binary(number: float) -> str:
    return "".join(str(1 & int(number) >> i) for i in reversed(range(16)))


def _check_oxyreduct(params: Mapping[str, Any], data: Mapping[int, float]) -> CheckResult:
    for tagid, value in data.items():
        ref_tagid = tagid
        if ref_tagid > 17:
            ref_tagid = ((ref_tagid - 18) % 8) + 10

        tag_params = _OXYREDUCT_TAG_MAP[ref_tagid]

        # if it's a measure, check levels
        if "name" in tag_params:
            if "condition_flag" in tag_params:
                condition_tagid = tagid + tag_params["condition_flag"][0]
                if not int(data[condition_tagid]) & tag_params["condition_flag"][1]:
                    continue

            value = value * float(tag_params.get("scale", 1.0))
            try:
                levels = params[tag_params["levels_name"]]
            except KeyError:
                levels = tag_params.get("levels", (16, 17, 14, 13))

            unit_str = tag_params.get("unit", "")
            yield from check_levels_v1(
                value,
                metric_name=tag_params.get("perfvar"),
                levels_lower=levels[2:],
                levels_upper=levels[:2],
                label=tag_params["name"],
                render_func=lambda v, u=unit_str: f"{v:.2f} {u}".strip(),
            )

        # if it's a bitmask, try to determine if they are good flags
        flags = tag_params.get("flags", [])
        for name, flag, value_bin in zip(
            tag_params.get("flag_names", []), flags, _to_binary(value)
        ):
            state = "active" if value_bin == "1" else "inactive"

            if flag in ("1", "0") and flag != value_bin:
                yield Result(state=State.CRIT, summary=f"{name} {state}")
            elif flag == "*":
                yield Result(state=State.OK, summary=f"{name} {state}")
            elif flag == "+" and value_bin == "1":
                yield Result(state=State.OK, summary=f"{name}")


def discovery_ewon(params: Mapping[Literal["device"], Any], section: Section) -> DiscoveryResult:
    device_name = params.get("device")

    yield Service(item="eWON Status", parameters={"device": device_name})

    if device_name == "oxyreduct":
        for item in _discovery_oxyreduct_names(section):
            yield Service(item=item, parameters={"device": device_name})


def check_ewon(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    device_name = params.get("device")
    if item == "eWON Status":
        if device_name is None:
            yield Result(
                state=State.WARN,
                summary="This device requires configuration. Please pick the device type.",
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"Configured for {device_name}",
            )
        return

    if device_name != "oxyreduct":
        return

    data = section.get(item)

    dev_results = list(_check_oxyreduct(params.get(device_name, {}), data)) if data else ()
    if dev_results:
        yield from dev_results
        return

    yield Result(state=State.OK, summary="No messages")


check_plugin_ewon = CheckPlugin(
    name="ewon",
    service_name="%s",
    discovery_function=discovery_ewon,
    discovery_default_parameters={
        "device": None,
    },
    discovery_ruleset_name="ewon_discovery_rules",
    check_function=check_ewon,
    check_default_parameters={},
    check_ruleset_name="ewon",
)
