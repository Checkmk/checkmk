#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import df, sap_hana


def parse_sap_hana_diskusage(string_table: StringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        for line in lines:
            if len(line) < 3:
                continue
            inst = section.setdefault(
                f"{sid_instance} - {line[0]}",
                {
                    "state_name": line[1],
                },
            )
            inst.update(_extract_size_and_used_from_line(line))
    return section


agent_section_sap_hana_diskusage = AgentSection(
    name="sap_hana_diskusage",
    parse_function=parse_sap_hana_diskusage,
)


def _extract_size_and_used_from_line(line: Sequence[str]) -> dict[str, float]:
    # Values are measured in GB. Are other factors possible? (Query)
    inst_values: dict[str, float] = {}
    splitted_line = line[-1].split()
    for key, index in [
        ("size", 1),
        ("used", 4),
    ]:
        try:
            inst_values[key] = float(splitted_line[index]) * 1024
        except (ValueError, IndexError):
            pass
    return inst_values


def discovery_sap_hana_diskusage(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_diskusage(
    item: str, params: Mapping[str, Any], section: sap_hana.ParsedSection
) -> CheckResult:
    data = section.get(item)
    if not data:
        raise IgnoreResultsError("Login into database failed.")

    state_name = data["state_name"]
    if state_name == "OK":
        state = State.OK
    elif state_name == "UNKNOWN":
        state = State.UNKNOWN
    else:
        state = State.CRIT
    yield Result(state=state, summary="Status: %s" % state_name)

    size_mb = data["size"]
    used_mb = data["used"]
    avail_mb = size_mb - used_mb
    yield from df.df_check_filesystem_list(
        get_value_store(),
        item,
        params,
        [(item, size_mb, avail_mb, 0)],
    )


check_plugin_sap_hana_diskusage = CheckPlugin(
    name="sap_hana_diskusage",
    service_name="SAP HANA Disk %s",
    discovery_function=discovery_sap_hana_diskusage,
    check_function=check_sap_hana_diskusage,
    check_ruleset_name="filesystem",
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
)
