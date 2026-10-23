#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any, TypedDict

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

# Channel status reported by the agent: parameter key of its service state
_STATUS_KEYS = {
    "INACTIVE": "inactive",
    "INITIALIZING": "initializing",
    "BINDING": "binding",
    "STARTING": "starting",
    "RUNNING": "running",
    "RETRYING": "retrying",
    "STOPPING": "stopping",
    "STOPPED": "stopped",
}

_FACTORY_STATES = {
    "inactive": 0,
    "initializing": 0,
    "binding": 0,
    "starting": 0,
    "running": 0,
    "retrying": 1,
    "stopping": 0,
    "stopped": 2,
}


class ChannelParams(TypedDict):
    mapped_states: Mapping[str, int]
    mapped_states_default: int


DEFAULT_PARAMETERS: ChannelParams = {
    "mapped_states": _FACTORY_STATES,
    "mapped_states_default": 3,
}


def map_ibm_mq_channel_status(status: str, params: ChannelParams) -> int:
    if (key := _STATUS_KEYS.get(status)) is None:
        return params["mapped_states_default"]
    # A rule may configure some of the states only.
    return params["mapped_states"].get(key, _FACTORY_STATES[key])


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
def check_ibm_mq_channels(item: str, params: ChannelParams, section: Any) -> CheckResult:
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
    check_default_parameters=DEFAULT_PARAMETERS,
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
