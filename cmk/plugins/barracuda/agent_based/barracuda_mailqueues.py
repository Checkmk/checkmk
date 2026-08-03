#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# .1.3.6.1.4.1.20632.2.2  0
# .1.3.6.1.4.1.20632.2.3  19
# .1.3.6.1.4.1.20632.2.4  17
# .1.3.6.1.4.1.20632.2.60 434

# Suggested by customer

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.barracuda.lib import DETECT_BARRACUDA


def discover_barracuda_mailqueues(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_barracuda_mailqueues(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    in_queue_str, active_queue_str, deferred_queue_str, daily_sent = section[0]
    for queue_type, queue in [
        ("Active", int(active_queue_str)),
        ("Deferred", int(deferred_queue_str)),
    ]:
        yield from check_levels(
            queue,
            levels_upper=("fixed", params[queue_type.lower()]),
            metric_name=f"mail_queue_{queue_type.lower()}_length",
            render_func=str,
            label=f"{queue_type} mails",
        )

    yield Result(state=State.OK, summary=f"Incoming mails: {in_queue_str}")
    if daily_sent:
        yield Result(state=State.OK, summary=f"Daily sent mails: {daily_sent}")


def parse_barracuda_mailqueues(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_barracuda_mailqueues = SimpleSNMPSection(
    name="barracuda_mailqueues",
    detect=DETECT_BARRACUDA,
    # The barracuda spam firewall does not response or returns a timeout error
    # executing 'snmpwalk' on whole tables. But we can workaround here specifying
    # all needed OIDs. Then we can use 'snmpget' and 'snmpwalk' on these single OIDs.
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20632.2",
        oids=["2", "3", "4", "60"],
    ),
    parse_function=parse_barracuda_mailqueues,
)


check_plugin_barracuda_mailqueues = CheckPlugin(
    name="barracuda_mailqueues",
    service_name="Mail Queue",
    discovery_function=discover_barracuda_mailqueues,
    check_function=check_barracuda_mailqueues,
    check_ruleset_name="mail_queue_length_single",
    check_default_parameters={
        "deferred": (80, 100),
        "active": (80, 100),
    },
)
