#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import suppress
from .utils import (
    sap_hana,
    df,
)

from .agent_based_api.v1 import (
    register,
    Service,
    Result,
    State as state,
    get_value_store,
)

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    AgentStringTable,
    CheckResult,
    Parameters,
)


def parse_sap_hana_data_volume(string_table: AgentStringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}

    MB = 1024**2

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        for line in lines:
            if len(line) < 8:
                continue

            for key_name, custom_dict, indexes in (
                ("%s - %s %s", {
                    "service": line[1],
                    "path": line[3]
                }, (7, 6)),
                ("%s - %s %s Disk", {}, (5, 4)),
                ("%s - %s %s Disk Net Data", {}, (5, 6)),
            ):

                inst = section.setdefault(key_name % (sid_instance, line[0], line[2]),
                                          custom_dict)  #  type: ignore
                for key, index in [
                    ("size", indexes[0]),
                    ("used", indexes[1]),
                ]:
                    with suppress(ValueError):
                        inst[key] = float(line[index]) / MB
    return section


register.agent_section(
    name="sap_hana_data_volume",
    parse_function=parse_sap_hana_data_volume,
)


def discovery_sap_hana_data_volume(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_data_volume(item: str, params: Parameters,
                               section: sap_hana.ParsedSection) -> CheckResult:
    item_data = section.get(item)
    if item_data is None:
        return
    size = item_data['size']
    used = item_data['used']
    avail = size - used

    yield from df.df_check_filesystem_list(get_value_store(), "sap_hana_data_volume", item, params,
                                           [(item, size, avail, 0)])

    service = item_data.get('service')
    if service:
        yield Result(state=state.OK, summary='Service: %s' % service)
    path = item_data.get('path')
    if path:
        yield Result(state=state.OK, summary='Path: %s' % path)

    # It ONE physical device and at least two nodes.
    # Thus we only need to check the first one.
    return


def cluster_check_sap_hana_data_volume(item, params, section):
    yield Result(state=state.OK, summary='Nodes: %s' % ', '.join(section.keys()))
    for node_section in section.values():
        if item in node_section:
            yield from check_sap_hana_data_volume(item, params, node_section)
            return


register.check_plugin(
    name="sap_hana_data_volume",
    service_name="SAP HANA Volume %s",
    discovery_function=discovery_sap_hana_data_volume,
    check_ruleset_name="filesystem",
    check_function=check_sap_hana_data_volume,
    check_default_parameters=df.FILESYSTEM_DEFAULT_LEVELS,
    cluster_check_function=cluster_check_sap_hana_data_volume,
)
