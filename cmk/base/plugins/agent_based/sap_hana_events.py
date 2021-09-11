#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from .agent_based_api.v1 import IgnoreResultsError, Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import sap_hana

SAP_HANA_EVENTS_MAP: Final = {
    "open_events": (State.CRIT, "Unacknowledged events"),
    "disabled_alerts": (State.WARN, "Disabled alerts"),
    "high_alerts": (State.CRIT, "High alerts"),
}


def parse_sap_hana_events(string_table: StringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        inst_data = {}
        for line in lines:
            if len(line) < 2:
                continue

            try:
                inst_data[line[0]] = int(line[1])
            except ValueError:
                pass
        section.setdefault(sid_instance, inst_data)
    return section


register.agent_section(
    name="sap_hana_events",
    parse_function=parse_sap_hana_events,
)


def discovery_sap_hana_events(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_events(item: str, section: sap_hana.ParsedSection) -> CheckResult:
    data = section.get(item)
    if not data:
        raise IgnoreResultsError("Login into database failed.")

    for event_key, event_count in data.items():
        event_state, event_state_readable = SAP_HANA_EVENTS_MAP.get(
            event_key, (State.UNKNOWN, "unknown[%s]" % event_key)
        )
        state = State.OK
        if event_count > 0:
            state = event_state
        yield Result(state=state, summary="%s: %s" % (event_state_readable, event_count))
        yield Metric("num_%s" % event_key, event_count)


register.check_plugin(
    name="sap_hana_events",
    service_name="SAP HANA Events %s",
    discovery_function=discovery_sap_hana_events,
    check_function=check_sap_hana_events,
)
