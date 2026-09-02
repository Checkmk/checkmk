#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.2604.1.1.1.4.1.2.1 Legit --> SOPHOS::counterType.1
# .1.3.6.1.4.1.2604.1.1.1.4.1.2.2 Blocked --> SOPHOS::counterType.2
# .1.3.6.1.4.1.2604.1.1.1.4.1.2.9 InvalidRecipient --> SOPHOS::counterType.9

# .1.3.6.1.4.1.2604.1.1.1.4.1.3.1 92 --> SOPHOS::counterInbound.1
# .1.3.6.1.4.1.2604.1.1.1.4.1.3.2 10 --> SOPHOS::counterInbound.2
# .1.3.6.1.4.1.2604.1.1.1.4.1.3.9 2 --> SOPHOS::counterInbound.9

# .1.3.6.1.4.1.2604.1.1.1.4.1.4.1 8 --> SOPHOS::counterOutbound.1
# .1.3.6.1.4.1.2604.1.1.1.4.1.4.2 0 --> SOPHOS::counterOutbound.2
# .1.3.6.1.4.1.2604.1.1.1.4.1.4.9 0 --> SOPHOS::counterOutbound.9

# TODO levels?


import time
from collections.abc import MutableMapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_rate,
    get_value_store,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def discover_sophos_messages(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0].replace("InvalidRecipient", "Invalid Recipient"))


def check_sophos_messages(item: str, section: StringTable) -> CheckResult:
    yield from _check_sophos_messages(item, section, get_value_store(), time.time())


def _check_sophos_messages(
    item: str,
    section: StringTable,
    value_store: MutableMapping[str, object],
    now: float,
) -> CheckResult:
    for counter_type, inbound_str, outbound_str in section:
        if counter_type.replace("InvalidRecipient", "Invalid Recipient") == item:
            inbound = get_rate(value_store, "inbound", now, int(inbound_str), raise_overflow=True)
            outbound = get_rate(
                value_store, "outbound", now, int(outbound_str), raise_overflow=True
            )
            yield Result(
                state=State.OK,
                summary=f"{inbound + outbound:.1f} Inbounds and Outbounds/s, {inbound:.1f} Inbounds/s, {outbound:.1f} Outbounds/s",
            )
            yield Metric("messages_inbound", inbound)
            yield Metric("messages_outbound", outbound)
            return


def parse_sophos_messages(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_sophos_messages = SimpleSNMPSection(
    name="sophos_messages",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2604"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2604.1.1.1.4.1",
        oids=["2", "3", "4"],
    ),
    parse_function=parse_sophos_messages,
)


check_plugin_sophos_messages = CheckPlugin(
    name="sophos_messages",
    service_name="Messages %s",
    discovery_function=discover_sophos_messages,
    check_function=check_sophos_messages,
)
