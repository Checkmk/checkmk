#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.fireeye.lib import DETECT

# .1.3.6.1.4.1.25597.13.1.44.0 0
# .1.3.6.1.4.1.25597.13.1.45.0 603
# .1.3.6.1.4.1.25597.13.1.46.0 8
# .1.3.6.1.4.1.25597.13.1.47.0 0
# .1.3.6.1.4.1.25597.13.1.48.0 96
# .1.3.6.1.4.1.25597.13.1.49.0 0

Section = Mapping[str, str]


def parse_fireeye_mailq(string_table: StringTable) -> Section | None:
    if string_table:
        return dict(zip(["Deferred", "Hold", "Incoming", "Active", "Drop"], string_table[0]))
    return None


def dicsover_fireeye_mailq(section: Section) -> DiscoveryResult:
    yield Service()


def check_fireeye_mailq(
    params: Mapping[str, tuple[float, float] | None], section: Section
) -> CheckResult:
    for queue, value in section.items():
        yield from check_levels(
            int(value),
            metric_name=f"mail_queue_{queue.lower()}_length",
            levels_upper=("fixed", levels)
            if (levels := params.get(queue.lower()))
            else ("no_levels", None),
            render_func=str,
            label=f"Mails in {queue.lower()} queue",
        )


snmp_section_fireeye_mailq = SimpleSNMPSection(
    name="fireeye_mailq",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=["44", "45", "47", "48", "49"],
    ),
    parse_function=parse_fireeye_mailq,
)


check_plugin_fireeye_mailq = CheckPlugin(
    name="fireeye_mailq",
    service_name="Mail Queues",
    discovery_function=dicsover_fireeye_mailq,
    check_function=check_fireeye_mailq,
    check_ruleset_name="fireeye_mailq",
    check_default_parameters={
        "deferred": (1, 50),
        "hold": (500, 1000),
        "drop": (50, 500),
    },
)
