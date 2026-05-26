#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.netapp import models

NtpSection = Mapping[str, models.NtpStatusModel]


class Params(TypedDict, total=False):
    offset: LevelsT[float]


def discover_netapp_ontap_time(section: NtpSection) -> DiscoveryResult:
    for node_name in section:
        yield Service(item=node_name)


def parse_netapp_ontap_time_status(string_table: StringTable) -> NtpSection:
    entries = [models.NtpStatusModel.model_validate_json(line[0]) for line in string_table]
    return {entry.node: entry for entry in entries}


agent_section_netapp_ontap_time = AgentSection(
    name="netapp_ontap_time",
    parse_function=parse_netapp_ontap_time_status,
)


def check_netapp_ontap_time(
    item: str,
    params: Params,
    section: NtpSection | None,
) -> CheckResult:
    if section is None:
        return

    node_status = section.get(item)
    if node_status is None:
        return

    if not node_status.peers:
        yield Result(state=State.CRIT, summary="No NTP server found")
        return

    selected_ntp = next(
        (peer for peer in node_status.peers if peer.is_peer_selected),
        None,
    )
    if selected_ntp is None:
        yield Result(state=State.CRIT, summary="No selected NTP server found")
        return

    if selected_ntp.offset is None:
        yield Result(state=State.CRIT, summary="Selected NTP server provided no offset")
        return

    yield Result(
        state=State.OK,
        notice=f"Selected NTP server: {selected_ntp.server}",
    )

    offset_seconds = abs(selected_ntp.offset) / 1000.0
    yield from check_levels(
        offset_seconds,
        levels_upper=params.get("offset"),
        metric_name="time_offset",
        render_func=render.timespan,
        label="Offset",
    )


check_plugin_netapp_ontap_time = CheckPlugin(
    name="netapp_ontap_time",
    service_name="System time Node %s",
    sections=["netapp_ontap_time"],
    discovery_function=discover_netapp_ontap_time,
    check_function=check_netapp_ontap_time,
    check_ruleset_name="netapp_ontap_time",
    check_default_parameters={"offset": ("fixed", (0.2, 0.5))},
)
