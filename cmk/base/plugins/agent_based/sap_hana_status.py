#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from .utils import sap_hana
from .agent_based_api.v1 import (
    register,
    Service,
    Result,
    State as state,
)

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    AgentStringTable,
    CheckResult,
)


def parse_sap_hana_status(string_table: AgentStringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        for line in lines:
            if line[0].lower() == "all started":
                item_name = 'Status'
                item_data = {
                    "instance": sid_instance,
                    "state_name": line[1],
                    "message": line[2],
                }
            else:  # Version
                item_name = line[0]
                item_data = {
                    "instance": sid_instance,
                    'version': line[2],
                }
            section.setdefault("%s %s" % (item_name, sid_instance), item_data)

    return section


register.agent_section(
    name="sap_hana_status",
    parse_function=parse_sap_hana_status,
)


def _check_sap_hana_status_data(data):
    state_name = data['state_name']
    if state_name.lower() == "ok":
        cur_state = state.OK
    elif state_name.lower() == "unknown":
        cur_state = state.CRIT
    else:
        cur_state = state.WARN
    return cur_state, "Status: %s" % state_name


def discovery_sap_hana_status(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_status(item: str, section: sap_hana.ParsedSection) -> CheckResult:

    data = section.get(item)
    if data is None:
        return

    if 'Status' in item:
        cur_state, infotext = _check_sap_hana_status_data(data)
        yield Result(state=cur_state, summary=infotext)
    else:
        yield Result(state=state.OK, summary="Version: %s" % data['version'])

    # It ONE physical device and at least two nodes.
    # Thus we only need to check the first one.
    return


def cluster_check_sap_hana_status(
    item: str,
    section: Dict[str, sap_hana.ParsedSection],
) -> CheckResult:

    yield Result(state=state.OK, summary='Nodes: %s' % ', '.join(section.keys()))
    for node_section in section.values():
        if item in node_section:
            yield from check_sap_hana_status(item, node_section)
            return


register.check_plugin(
    name="sap_hana_status",
    service_name="SAP HANA %s",
    discovery_function=discovery_sap_hana_status,
    check_function=check_sap_hana_status,
    cluster_check_function=cluster_check_sap_hana_status,
)
