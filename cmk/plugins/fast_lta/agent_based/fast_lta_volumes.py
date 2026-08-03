#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS, FSBlock

Section = Mapping[str, list[FSBlock]]


def parse_fast_lta_volumes(string_table: StringTable) -> Section:
    parsed: dict[str, list[FSBlock]] = {}
    for volname, volquota, volused in string_table:
        try:
            quota_bytes = int(volquota)
            used_bytes = int(volused)
        except ValueError:
            continue
        parsed.setdefault(volname, []).append(
            (volname, quota_bytes / 1048576.0, (quota_bytes - used_bytes) / 1048576.0, 0)
        )

    return parsed


def discover_fast_lta_volumes(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_fast_lta_volumes(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=data,
    )


snmp_section_fast_lta_volumes = SimpleSNMPSection(
    name="fast_lta_volumes",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        any_of(exists(".1.3.6.1.4.1.27417.5.1.1.2"), exists(".1.3.6.1.4.1.27417.5.1.1.2.0")),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.27417.5.1.1",
        oids=["2", "9", "11"],
    ),
    parse_function=parse_fast_lta_volumes,
)

check_plugin_fast_lta_volumes = CheckPlugin(
    name="fast_lta_volumes",
    service_name="Fast LTA Volume %s",
    discovery_function=discover_fast_lta_volumes,
    check_function=check_fast_lta_volumes,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
