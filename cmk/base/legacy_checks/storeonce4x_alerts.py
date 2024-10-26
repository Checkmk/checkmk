#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Literal

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

Section = Mapping[Literal["alerts"], Sequence[Mapping[str, Any]]]


STATUS_MAP = {"CRITICAL": 2, "WARNING": 1, "OK": 0, "UNKNOWN": 3, "DISABLED": 3}


def parse_storeonce4x_alerts(string_table):
    return {
        "alerts": [
            {
                "cleared": alert["state"].upper() == "CLEARED",
                "status": STATUS_MAP[alert["status"].upper()],
                "alertState": alert["alertState"],
                "description": alert["description"],
            }
            for alert in json.loads(string_table[0][0])["members"]
        ]
    }


def discover_storeonce4x_alerts(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_storeonce4x_alerts(_item, _param, parsed):
    if not parsed["alerts"]:
        yield 0, "No alerts at all found"
        return

    if all(alert["cleared"] for alert in parsed["alerts"]):
        yield 0, "No uncleared alerts found"
        return

    yield from (
        (
            alert["status"],
            f"Alert State: {alert['alertState']}, Description: {alert['description']}",
        )
        for alert in parsed["alerts"]
        if not alert["cleared"]
    )


check_info["storeonce4x_alerts"] = LegacyCheckDefinition(
    name="storeonce4x_alerts",
    parse_function=parse_storeonce4x_alerts,
    service_name="Alerts",
    discovery_function=discover_storeonce4x_alerts,
    check_function=check_storeonce4x_alerts,
)
