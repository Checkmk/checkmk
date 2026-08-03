#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# .1.3.6.1.4.1.393.200.130.2.1.2.1 = INTEGER: 1
# .1.3.6.1.4.1.393.200.130.2.1.2.2 = INTEGER: 1
# .1.3.6.1.4.1.393.200.130.2.2.1.1.1.1 = INTEGER: 1
# .1.3.6.1.4.1.393.200.130.2.2.1.1.1.2 = INTEGER: 2
# .1.3.6.1.4.1.393.200.130.2.2.1.1.1.3 = INTEGER: 3
# .1.3.6.1.4.1.393.200.130.2.2.1.1.2.1 = STRING: "delivery"
# .1.3.6.1.4.1.393.200.130.2.2.1.1.2.2 = STRING: "inbound"
# .1.3.6.1.4.1.393.200.130.2.2.1.1.2.3 = STRING: "outbound"
# .1.3.6.1.4.1.393.200.130.2.2.1.1.3.1 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.3.2 = Gauge32: 1
# .1.3.6.1.4.1.393.200.130.2.2.1.1.3.3 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.4.1 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.4.2 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.4.3 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.5.1 = Gauge32: 4
# .1.3.6.1.4.1.393.200.130.2.2.1.1.5.2 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.5.3 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.6.1 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.6.2 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.6.3 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.7.1 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.7.2 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.7.3 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.8.1 = Gauge32: 5
# .1.3.6.1.4.1.393.200.130.2.2.1.1.8.2 = Gauge32: 0
# .1.3.6.1.4.1.393.200.130.2.2.1.1.8.3 = Gauge32: 0


import contextlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

Section = dict[str, dict[str, int]]


def parse_sym_brightmail_queues(string_table: StringTable) -> Section:
    parsed: Section = {}
    for (
        descr,
        connections,
        dataRate,
        deferredMessages,
        messageRate,
        queueSize,
        queuedMessages,
    ) in string_table:
        for k, v in [
            ("connections", connections),
            ("dataRate", dataRate),
            ("deferredMessages", deferredMessages),
            ("messageRate", messageRate),
            ("queueSize", queueSize),
            ("queuedMessages", queuedMessages),
        ]:
            with contextlib.suppress(ValueError):
                parsed.setdefault(descr, {})[k] = int(v)
    return parsed


def discover_sym_brightmail_queues(section: Section) -> DiscoveryResult:
    yield from (Service(item=descr) for descr in section)


def check_sym_brightmail_queues(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if item not in section:
        return

    data = section[item]
    for key, title in [
        ("connections", "Connections"),
        ("dataRate", "Data rate"),
        ("deferredMessages", "Deferred messages"),
        ("messageRate", "Message rate"),
        # Symantec did not document the Unit for the queue. You can still set
        # some level if you wish.
        ("queueSize", "Queue size"),
        ("queuedMessages", "Queued messages"),
    ]:
        value = data.get(key)
        if value is not None:
            raw_levels: tuple[int, int] | None = params.get(key)
            yield from check_levels(
                value,
                levels_upper=("fixed", raw_levels) if raw_levels is not None else None,
                label=title,
            )


snmp_section_sym_brightmail_queues = SimpleSNMPSection(
    name="sym_brightmail_queues",
    detect=any_of(contains(".1.3.6.1.2.1.1.1.0", "el5_sms"), contains(".1.3.6.1.2.1.1.1.0", "el6")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.393.200.130.2.2.1.1",
        oids=["2", "3", "4", "5", "6", "7", "8"],
    ),
    parse_function=parse_sym_brightmail_queues,
)

check_plugin_sym_brightmail_queues = CheckPlugin(
    name="sym_brightmail_queues",
    service_name="Queue %s",
    discovery_function=discover_sym_brightmail_queues,
    check_function=check_sym_brightmail_queues,
    check_ruleset_name="sym_brightmail_queues",
    check_default_parameters={},
)
