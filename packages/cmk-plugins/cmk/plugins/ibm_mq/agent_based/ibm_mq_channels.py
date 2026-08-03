#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.plugins.ibm_mq.lib import is_ibm_mq_service_vanished, parse_ibm_mq

# <<<ibm_mq_channels:sep(10)>>>
# QMNAME(MY.TEST)                                           STATUS(RUNNING)
# 5724-H72 (C) Copyright IBM Corp. 1994, 2015.
# Starting MQSC for queue manager MY.TEST.
#
# AMQ8414: Display Channel details.
#    CHANNEL(MY.SENDER.ONE)                  CHLTYPE(SDR)
#    XMITQ(MY.SENDER.ONE.XMIT)
# AMQ8417: Display Channel Status details.
#    CHANNEL(MY.SENDER.ONE)                  CHLTYPE(SDR)
#    CONNAME(99.999.999.999(1414),44.555.666.777(1414))
#    CURRENT                                 RQMNAME( )
#    STATUS(RETRYING)                        SUBSTATE( )
#    XMITQ(MY.SENDER.ONE.XMIT)
# 3 MQSC commands read.
# No commands have a syntax error.
# One valid MQSC command could not be processed.

Section = Mapping[str, Mapping[str, str]]


def parse_ibm_mq_channels(string_table: StringTable) -> Section:
    return parse_ibm_mq(string_table, "CHANNEL")


agent_section_ibm_mq_channels = AgentSection(
    name="ibm_mq_channels",
    parse_function=parse_ibm_mq_channels,
)

_DEFAULT_STATUS_MAP = {
    "INACTIVE": ("inactive", 0),
    "INITIALIZING": ("initializing", 0),
    "BINDING": ("binding", 0),
    "STARTING": ("starting", 0),
    "RUNNING": ("running", 0),
    "RETRYING": ("retrying", 1),
    "STOPPING": ("stopping", 0),
    "STOPPED": ("stopped", 2),
}


def map_ibm_mq_channel_status(status: str, params: Mapping[str, Any]) -> int:
    wato_key, check_state = _DEFAULT_STATUS_MAP.get(status, ("unknown", 3))
    if "mapped_states" in params:
        mapped_states = dict(params["mapped_states"])
        if wato_key in mapped_states:
            check_state = mapped_states[wato_key]
        elif "mapped_states_default" in params:
            check_state = params["mapped_states_default"]
    return check_state


def discover_ibm_mq_channels(section: Any) -> DiscoveryResult:
    for service_name in section:
        if ":" not in service_name:
            # Do not show queue manager entry in inventory
            continue
        yield Service(item=service_name)


#
# See http://www-01.ibm.com/support/docview.wss?uid=swg21667353
# or search for 'inactive channels' in 'display chstatus' command manual
# to learn more about INACTIVE status of channels
#
def check_ibm_mq_channels(item: str, params: Mapping[str, Any], section: Any) -> CheckResult:
    if is_ibm_mq_service_vanished(item, section):
        return
    data = section[item]
    status = data.get("STATUS", "INACTIVE")
    check_state = map_ibm_mq_channel_status(status, params)
    chltype = data.get("CHLTYPE")
    infotext = f"Status: {status}, Type: {chltype}"
    if "XMITQ" in data:
        infotext += f", Xmitq: {data['XMITQ']}"
    yield Result(state=State(check_state), summary=infotext)


check_plugin_ibm_mq_channels = CheckPlugin(
    name="ibm_mq_channels",
    service_name="IBM MQ Channel %s",
    discovery_function=discover_ibm_mq_channels,
    check_function=check_ibm_mq_channels,
    check_ruleset_name="ibm_mq_channels",
    check_default_parameters={},
)


def inventorize_ibm_mq_channels(section: Section) -> InventoryResult:
    for item, attrs in section.items():
        if ":" not in item:
            # Do not show queue manager in inventory
            continue

        qmname, cname = item.split(":")
        yield TableRow(
            path=["software", "applications", "ibm_mq", "channels"],
            key_columns={
                "qmgr": qmname,
                "name": cname,
            },
            inventory_columns={
                "type": attrs.get("CHLTYPE", "Unknown"),
                "monchl": attrs.get("MONCHL", "n/a"),
            },
            status_columns={
                "status": attrs.get("STATUS", "Unknown"),
            },
        )


inventory_plugin_ibm_mq_channels = InventoryPlugin(
    name="ibm_mq_channels",
    inventory_function=inventorize_ibm_mq_channels,
)
