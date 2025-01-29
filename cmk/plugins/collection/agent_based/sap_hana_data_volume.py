#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from contextlib import suppress
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


def parse_sap_hana_data_volume(string_table: StringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}

    MB = 1024**2

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        for line in lines:
            if len(line) < 8:
                continue

            line_parsing_schema: Sequence[tuple[str, dict[str, str], tuple[int, int]]] = [
                ("%s - %s %s", {"service": line[1], "path": line[3]}, (7, 6)),
                ("%s - %s %s Disk", {}, (5, 4)),
                ("%s - %s %s Disk Net Data", {}, (5, 6)),
            ]
            for key_name, custom_dict, indexes in line_parsing_schema:
                inst = section.setdefault(key_name % (sid_instance, line[0], line[2]), custom_dict)
                for key, index in [
                    ("size", indexes[0]),
                    ("used", indexes[1]),
                ]:
                    with suppress(ValueError):
                        inst[key] = float(line[index]) / MB
    return section


agent_section_sap_hana_data_volume = AgentSection(
    name="sap_hana_data_volume",
    parse_function=parse_sap_hana_data_volume,
)


def discovery_sap_hana_data_volume(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_data_volume(
    item: str, params: Mapping[str, Any], section: sap_hana.ParsedSection
) -> CheckResult:
    item_data = section.get(item)
    if not item_data:
        raise IgnoreResultsError("Login into database failed.")
    size = item_data["size"]
    used = item_data["used"]
    avail = size - used

    yield from df.df_check_filesystem_list(
        get_value_store(),
        item,
        params,
        [(item, size, avail, 0)],
    )

    service = item_data.get("service")
    if service:
        yield Result(state=State.OK, summary="Service: %s" % service)
    path = item_data.get("path")
    if path:
        yield Result(state=State.OK, summary="Path: %s" % path)


def cluster_check_sap_hana_data_volume(item, params, section):
    yield Result(state=State.OK, summary="Nodes: %s" % ", ".join(section.keys()))
    for node_section in section.values():
        if item in node_section:
            yield from check_sap_hana_data_volume(item, params, node_section)
            return


check_plugin_sap_hana_data_volume = CheckPlugin(
    name="sap_hana_data_volume",
    service_name="SAP HANA Volume %s",
    discovery_function=discovery_sap_hana_data_volume,
    check_ruleset_name="filesystem",
    check_function=check_sap_hana_data_volume,
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
    cluster_check_function=cluster_check_sap_hana_data_volume,
)
