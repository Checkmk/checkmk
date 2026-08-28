#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# Nikolas Hagemann, comNET GmbH - nikolas.hagemann@comnetgmbh.com

# Example output:
# .1.3.6.1.4.1.12356.118.5.1.1.0 0
# .1.3.6.1.4.1.12356.118.5.1.2.0 0
# .1.3.6.1.4.1.12356.118.5.1.3.0 0
# .1.3.6.1.4.1.12356.118.5.1.4.0 0
# .1.3.6.1.4.1.12356.118.5.1.5.0 0
# .1.3.6.1.4.1.12356.118.5.1.6.0 0
# .1.3.6.1.4.1.12356.118.5.1.7.0 0
# .1.3.6.1.4.1.12356.118.5.1.8.0 0
# .1.3.6.1.4.1.12356.118.5.1.9.0 0
# .1.3.6.1.4.1.12356.118.5.1.10.0 0
# .1.3.6.1.4.1.12356.118.5.1.11.0 0

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.fortinet.lib import DETECT_FORTISANDBOX

Section = Mapping[str, int]

_QUEUES = (
    "Executable",
    "PDF",
    "Office",
    "Flash",
    "Web",
    "Android",
    "MAC",
    "URL job",
    "User defined",
    "Non Sandboxing",
    "Job Queue Assignment",
)


def parse_fortisandbox_queues(string_table: StringTable) -> Section | None:
    return {k: int(v) for k, v in zip(_QUEUES, string_table[0])} if string_table else None


def discover_fortisandbox_queues(section: Section) -> DiscoveryResult:
    for queue in section:
        yield Service(item=queue)


def check_fortisandbox_queues(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (length := section.get(item)) is None:
        return

    yield from check_levels_v1(
        length,
        metric_name="queue",
        levels_upper=params.get("length"),
        render_func=str,
        label="Queue length",
    )


snmp_section_fortisandbox_queues = SimpleSNMPSection(
    name="fortisandbox_queues",
    detect=DETECT_FORTISANDBOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.118.5.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
    ),
    parse_function=parse_fortisandbox_queues,
)


check_plugin_fortisandbox_queues = CheckPlugin(
    name="fortisandbox_queues",
    service_name="Pending %s files",
    discovery_function=discover_fortisandbox_queues,
    check_function=check_fortisandbox_queues,
    check_ruleset_name="fortisandbox_queues",
    check_default_parameters={},
)
