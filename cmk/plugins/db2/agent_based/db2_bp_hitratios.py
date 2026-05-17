#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs

Section = Mapping[str, list[list[str]]]

# <<<db2_bp_hitratios>>>
# [[[db2taddm:CMDBS1]]]
# BP_NAME        TOTAL_HIT_RATIO_PERCENT DATA_HIT_RATIO_PERCENT INDEX_HIT_RATIO_PERCENT XDA_HIT_RATIO_PERCENT
# IBMDEFAULTBP                     99.36                  98.48                   99.94                     -
# BUF8K                            99.94                  99.94                   99.95                     -
# BUF32K                           99.99                  99.98                   99.99                     -
# BP8                             100.00                 100.00                       -                     -


def parse_db2_bp_hitratios(string_table: StringTable) -> Section:
    pre_parsed = parse_db2_dbs(string_table)

    # Some databases run in DPF mode. This means they are split over several instances
    # Each instance has its own bufferpool hitratio information. We create on service for each instance
    databases: dict[str, list[list[str]]] = {}
    for instance, lines in pre_parsed[1].items():
        header_idx: int | None = None
        node_names: list[str] = []
        node_headers: list[str] = []
        for idx, line in enumerate(lines):
            if line[0] == "node":
                node_names.append(" ".join(line[1:]))
            elif line[0] == "BP_NAME":
                header_idx = idx
                node_headers = line
                break

        if node_names:
            if header_idx is None:
                continue
            # DPF mode
            current_node_offset = -1
            current_instance: str | None = None
            for line in lines[header_idx + 1 :]:
                if line[0] == "IBMDEFAULTBP":
                    current_node_offset += 1
                    current_instance = f"{instance} DPF {node_names[current_node_offset]}"
                    databases.setdefault(current_instance, [node_headers])
                if current_instance in databases:
                    databases[current_instance].append(line)
        else:
            databases[instance] = lines

    return databases


def discover_db2_bp_hitratios(section: Section) -> DiscoveryResult:
    for key, values in section.items():
        for field in values[1:]:
            if not field[0].startswith("IBMSYSTEMBP"):
                yield Service(item=f"{key}:{field[0]}")


_KEY_TO_TEXT = {
    "TOTAL_HIT": "Total",
    "DATA_HIT": "Data",
    "INDEX_HIT": "Index",
    "XDA_HIT": "XDA",
}


def check_db2_bp_hitratios(item: str, section: Section) -> CheckResult:
    db_instance, field = item.rsplit(":", 1)
    db = section.get(db_instance)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    headers = db[0]
    for line in db[1:]:
        if field != line[0]:
            continue
        hr_info = dict(zip(headers[1:], line[1:]))  # skip BP_NAME
        for header in headers[1:]:
            value = hr_info[header].replace("-", "0").replace(",", ".")
            key = header.replace("_RATIO_PERCENT", "")
            float_value = float(value)
            yield Result(state=State.OK, summary=f"{_KEY_TO_TEXT[key]}: {value}%")
            yield Metric(f"{key.lower()}ratio", float_value, boundaries=(0.0, 100.0))
        break


agent_section_db2_bp_hitratios = AgentSection(
    name="db2_bp_hitratios",
    parse_function=parse_db2_bp_hitratios,
)


check_plugin_db2_bp_hitratios = CheckPlugin(
    name="db2_bp_hitratios",
    service_name="DB2 BP-Hitratios %s",
    discovery_function=discover_db2_bp_hitratios,
    check_function=check_db2_bp_hitratios,
)
