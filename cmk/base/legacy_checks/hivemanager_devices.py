#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<hivemanager_devices:sep(124)>>>
# BBSA-WIFI-LSN-Rhod-F4-1|8|Cleared|True|21 Days, 17 Hrs 43 Mins 43 Secs
# BBSA-WIFI-LSN-Rhod-F4-2|8|Cleared|True|21 Days, 17 Hrs 43 Mins 43 Secs
# BBSA-WIFI-LSN-Hald-F4-1|4|Cleared|True|2 Days, 0 Hrs 30 Mins 41 Secs
# BBSA-WIFI-LSN-Hald-F2-1|24|Cleared|True|57 Days, 3 Hrs 24 Mins 22 Secs


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable

check_info = {}

TOKEN_MULTIPLIER = (1, 60, 3600, 86400, 31536000)


def discover_hivemanager_devices(info):
    for line in info:
        infos = dict([x.split("::") for x in line])
        yield infos["hostName"], {}


def check_hivemanager_devices(item, params, info):
    for line in info:
        infos = dict([x.split("::") for x in line])
        if infos["hostName"] == item:
            # Check for Alarm State
            alarmstate = "Alarm state: " + infos["alarm"]
            if infos["alarm"] in params["warn_states"]:
                yield 1, alarmstate
            elif infos["alarm"] in params["crit_states"]:
                yield 2, alarmstate

            # If activated, Check for lost connection of client
            if params["alert_on_loss"]:
                if infos["connection"] == "False":
                    yield 2, "Connection lost"

            # The number of clients
            number_of_clients = int(infos["clients"])
            warn, crit = params["max_clients"]

            perfdata = [("client_count", number_of_clients, warn, crit)]
            infotext = "Clients: %s" % number_of_clients
            levels = f" Warn/Crit at {warn}/{crit}"

            if number_of_clients >= crit:
                yield 2, infotext + levels, perfdata
            elif number_of_clients >= warn:
                yield 1, infotext + levels, perfdata
            else:
                yield 0, infotext, perfdata

            # Uptime
            if (raw_uptime := infos["upTime"]) != "down":
                yield check_levels(
                    sum(
                        factor * int(token)
                        for factor, token in zip(TOKEN_MULTIPLIER, raw_uptime.split()[-2::-2])
                    ),
                    "uptime",
                    params.get("max_uptime"),
                    human_readable_func=render.timespan,
                    infoname="Uptime",
                )

            # Additional Information
            additional_informations = [
                "eth0LLDPPort",
                "eth0LLDPSysName",
                "hive",
                "hiveOS",
                "hwmodel",
                "serialNumber",
                "nodeId",
                "location",
                "networkPolicy",
            ]
            yield (
                0,
                ", ".join(
                    [
                        f"{x}: {y}"
                        for x, y in infos.items()
                        if x in additional_informations and y != "-"
                    ]
                ),
            )


def parse_hivemanager_devices(string_table: StringTable) -> StringTable:
    return string_table


check_info["hivemanager_devices"] = LegacyCheckDefinition(
    name="hivemanager_devices",
    parse_function=parse_hivemanager_devices,
    service_name="Client %s",
    discovery_function=discover_hivemanager_devices,
    check_function=check_hivemanager_devices,
    check_ruleset_name="hivemanager_devices",
    check_default_parameters={
        "alert_on_loss": True,
        "max_clients": (25, 50),
        "crit_states": ["Critical"],
        "warn_states": ["Maybe", "Major", "Minor"],
    },
)
