#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer untile we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

TOKEN_MULTIPLIER = (1, 60, 3600, 86400, 31536000)

Section = Mapping[str, Mapping[str, str]]


def discover_hivemanager_devices(section: Section) -> DiscoveryResult:
    for host_name in section:
        yield Service(item=host_name)


def check_hivemanager_devices(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (infos := section.get(item)):
        return

    # Check for Alarm State
    alarmstate = "Alarm state: " + infos["alarm"]
    if infos["alarm"] in params["warn_states"]:
        yield Result(state=State.WARN, summary=alarmstate)
    elif infos["alarm"] in params["crit_states"]:
        yield Result(state=State.CRIT, summary=alarmstate)

    # If activated, Check for lost connection of client
    if params["alert_on_loss"]:
        if infos["connection"] == "False":
            yield Result(state=State.CRIT, summary="Connection lost")

    # The number of clients
    number_of_clients = int(infos["clients"])
    warn, crit = params["max_clients"]

    infotext = f"Clients: {number_of_clients}"
    levels = f" Warn/Crit at {warn}/{crit}"

    if number_of_clients >= crit:
        yield Result(state=State.CRIT, summary=infotext + levels)
    elif number_of_clients >= warn:
        yield Result(state=State.WARN, summary=infotext + levels)
    else:
        yield Result(state=State.OK, summary=infotext)
    yield Metric("client_count", number_of_clients, levels=(warn, crit))

    # Uptime
    if (raw_uptime := infos["upTime"]) != "down":
        yield from check_levels(
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
    yield Result(
        state=State.OK,
        summary=", ".join(
            [f"{x}: {y}" for x, y in infos.items() if x in additional_informations and y != "-"]
        ),
    )


def parse_hivemanager_devices(string_table: StringTable) -> Section:
    return {
        infos["hostName"]: infos
        for line in string_table
        for infos in (dict(x.split("::") for x in line),)
    }


agent_section_hivemanager_devices = AgentSection(
    name="hivemanager_devices",
    parse_function=parse_hivemanager_devices,
)


check_plugin_hivemanager_devices = CheckPlugin(
    name="hivemanager_devices",
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
