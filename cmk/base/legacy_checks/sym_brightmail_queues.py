#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

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


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, contains, SNMPTree

check_info = {}


def parse_sym_brightmail_queues(string_table):
    parsed = {}
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
            try:
                parsed.setdefault(descr, {}).setdefault(k, int(v))
            except ValueError:
                pass
    return parsed


def discover_sym_brightmail_queues(parsed):
    for descr in parsed:
        yield descr, {}


def check_sym_brightmail_queues(item, params, parsed):
    if item not in parsed:
        yield
        return

    data = parsed[item]
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
            yield check_levels(value, None, params.get(key), infoname=title)


check_info["sym_brightmail_queues"] = LegacyCheckDefinition(
    name="sym_brightmail_queues",
    detect=any_of(contains(".1.3.6.1.2.1.1.1.0", "el5_sms"), contains(".1.3.6.1.2.1.1.1.0", "el6")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.393.200.130.2.2.1.1",
        oids=["2", "3", "4", "5", "6", "7", "8"],
    ),
    parse_function=parse_sym_brightmail_queues,
    service_name="Queue %s",
    discovery_function=discover_sym_brightmail_queues,
    check_function=check_sym_brightmail_queues,
    check_ruleset_name="sym_brightmail_queues",
)
