#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.mbg_lantime import DETECT_MBG_LANTIME_NG

check_info = {}


def parse_mbg_lantime_ng_fan(string_table):
    parsed = {}
    fan_states = {
        "0": (3, "not available"),
        "1": (2, "off"),
        "2": (0, "on"),
    }
    fan_errors = {
        "0": (0, "not available"),
        "1": (0, "no"),
        "2": (2, "yes"),
    }

    for line in string_table:
        index, fan_status, fan_error = line
        if not index:
            continue

        fan_state, fan_state_name = fan_states.get(
            fan_status,
            (3, "not available"),
        )
        error_state, error_name = fan_errors.get(
            fan_error,
            (3, "not available"),
        )

        parsed.setdefault(
            index,
            {
                "status": {"state": fan_state, "name": fan_state_name},
                "error": {"state": error_state, "name": error_name},
            },
        )

    return parsed


def discover_mbg_lantime_ng_fan(section):
    yield from (
        (item, {}) for item, data in section.items() if data["status"]["name"] != "not available"
    )


def check_mbg_lantime_ng_fan(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return

    fan_status = data["status"]
    yield fan_status["state"], "Status: %s" % fan_status["name"]

    fan_error = data["error"]
    yield fan_error["state"], "Errors: %s" % fan_error["name"]


check_info["mbg_lantime_ng_fan"] = LegacyCheckDefinition(
    name="mbg_lantime_ng_fan",
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.5.1.2.1",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_mbg_lantime_ng_fan,
    service_name="Fan %s",
    discovery_function=discover_mbg_lantime_ng_fan,
    check_function=check_mbg_lantime_ng_fan,
)
