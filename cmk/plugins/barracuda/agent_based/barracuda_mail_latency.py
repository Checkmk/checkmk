#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# .1.3.6.1.4.1.20632.2.5 2


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.barracuda.lib import DETECT_BARRACUDA


def discover_barracuda_mail_latency(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_barracuda_mail_latency(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    yield from check_levels(
        int(section[0][0]),
        levels_upper=("no_levels", None) if (l := params["levels"]) is None else ("fixed", l),
        metric_name="mail_latency",
        render_func=render.timespan,
        label="Average",
    )


def parse_barracuda_mail_latency(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_barracuda_mail_latency = SimpleSNMPSection(
    name="barracuda_mail_latency",
    detect=DETECT_BARRACUDA,
    # The barracuda spam firewall does not response or returns a timeout error
    # executing 'snmpwalk' on whole tables. But we can workaround here specifying
    # all needed OIDs. Then we can use 'snmpget' and 'snmpwalk' on these single OIDs.
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20632.2",
        oids=["5"],
    ),
    parse_function=parse_barracuda_mail_latency,
)


check_plugin_barracuda_mail_latency = CheckPlugin(
    name="barracuda_mail_latency",
    service_name="Mail Latency",
    discovery_function=discover_barracuda_mail_latency,
    check_function=check_barracuda_mail_latency,
    check_ruleset_name="mail_latency",
    check_default_parameters={
        # Suggested by customer, in seconds
        "levels": (40, 60),
    },
)
