#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.fortinet import DETECT_FORTIMAIL

Section = Mapping[str, Mapping[str, int]]


def parse_fortimail_queue(string_table: StringTable) -> Section:
    """
    >>> parse_fortimail_queue([["default queue", 31, 534], ["incoming slow queue", 0, 0]])
    {'default queue': {'length': 31, 'size': 546816}, 'incoming slow queue': {'length': 0, 'size': 0}}
    """
    return {
        sub_table[0]: {
            "length": int(sub_table[1]),
            "size": int(sub_table[2]) * 1024,
        }
        for sub_table in string_table
    }


def discover_fortimail_queue(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section)


def check_fortimail_queue(
    item: str,
    params: Mapping[str, tuple[float, float] | None],
    section: Section,
) -> CheckResult:
    if not (queue_data := section.get(item)):
        return
    yield from check_levels_v1(
        queue_data["length"],
        levels_upper=params["queue_length"],
        metric_name="mail_queue_active_length",
        label="Length",
        render_func=str,
    )
    yield from check_levels_v1(
        queue_data["size"],
        metric_name="mail_queue_active_size",
        label="Size",
        render_func=render.bytes,
    )


snmp_section_fortimail_queue = SimpleSNMPSection(
    name="fortimail_queue",
    parse_function=parse_fortimail_queue,
    detect=DETECT_FORTIMAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.105.1.103.2.1",
        oids=[
            "2",  # fmlMailQueueName
            "3",  # fmlMailQueueMailCount
            "4",  # fmlMailQueueMailSize
        ],
    ),
)

check_plugin_fortimail_queue = CheckPlugin(
    name="fortimail_queue",
    service_name="FortiMail %s",
    discovery_function=discover_fortimail_queue,
    check_function=check_fortimail_queue,
    check_default_parameters={"queue_length": (100, 200)},
    check_ruleset_name="fortimail_queue",
)
