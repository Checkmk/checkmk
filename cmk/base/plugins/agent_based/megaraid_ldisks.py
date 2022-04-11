#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import megaraid

# Example output from agent:
# Adapter 0 -- Virtual Drive Information:
# Virtual Disk: 0 (Target Id: 0)
# Size:139488MB
# State: Optimal
# Stripe Size: 64kB
# Number Of Drives:2
# Adapter 1: No Virtual Drive Configured.


def megaraid_ldisks_is_new_drive(l):
    return (
        l.startswith("Virtual Disk:")
        or l.startswith("Virtual Drive:")
        or l.startswith("CacheCade Virtual Drive:")
    )


def parse_megaraid_ldisks(string_table: StringTable) -> megaraid.SectionLDisks:
    parsed: dict[str, dict[str, str]] = {}
    adapter = None
    disk = None
    item = None
    for line in string_table:
        l = " ".join(line)
        if line[0] == "Adapter" and not l.endswith("No Virtual Drive Configured."):
            adapter = line[1]
        elif megaraid_ldisks_is_new_drive(l) and adapter is not None:
            disk = l.split(": ")[1].split(" ")[0]
            item = "/c{adapter}/v{disk}"
            parsed[item] = {}

            # Add it under the old item name. Not discovered, but can be used when checking
            legacy_item = "%d/%d" % (int(adapter), int(disk))
            parsed[legacy_item] = parsed[item]

        elif item is not None and item in parsed:

            if line[0].startswith("State"):
                parsed[item]["state"] = l.split(":")[1].strip()
            elif line[0].startswith("Default"):
                if line[1].startswith("Cache"):
                    parsed[item]["default_cache"] = " ".join(line[3:]).replace(": ", "")
                elif line[1].startswith("Write"):
                    parsed[item]["default_write"] = " ".join(line[3:]).replace(": ", "")

            elif line[0].startswith("Current"):
                if line[1].startswith("Cache"):
                    parsed[item]["current_cache"] = " ".join(line[3:]).replace(": ", "")
                elif line[1].startswith("Write"):
                    parsed[item]["current_write"] = " ".join(line[3:]).replace(": ", "")

    return {k: megaraid.LDisk(**v) for k, v in parsed.items() if "state" in v}


register.agent_section(
    name="megaraid_ldisks",
    parse_function=parse_megaraid_ldisks,
)


def discover_megaraid_ldisks(section: megaraid.SectionLDisks) -> DiscoveryResult:
    # Items changed from e.g. '1/2' to '/c1/v2' for consistency.
    # Only discover the new-style items.
    # The old items are kept in section, so that old services using them will still produce results
    yield from (Service(item=item) for item in section if item.startswith("/c"))


def check_megaraid_ldisks(
    item: str,
    params: Mapping[str, int],
    section: megaraid.SectionLDisks,
) -> CheckResult:
    if (ldisk := section.get(item)) is None:
        return

    yield Result(state=State(params.get(ldisk.state, 3)), summary=f"{ldisk.state.capitalize()}")

    if default_cache := ldisk.default_cache:
        yield megaraid.check_state(State.WARN, "Cache", ldisk.current_cache, default_cache)

    if default_write := ldisk.default_write:
        yield megaraid.check_state(State.WARN, "Write", ldisk.current_write, default_write)


register.check_plugin(
    name="megaraid_ldisks",
    discovery_function=discover_megaraid_ldisks,
    check_function=check_megaraid_ldisks,
    check_default_parameters=megaraid.LDISKS_DEFAULTS,
    check_ruleset_name="storcli_vdrives",
    service_name="RAID logical disk %s",
)
