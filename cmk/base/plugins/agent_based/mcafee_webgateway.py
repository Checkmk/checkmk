#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import typing

from cmk.base.plugins.agent_based.agent_based_api import v1

Section = typing.Any
Params = dict


def discover_mcafee_gateway(section: Section) -> v1.type_defs.DiscoveryResult:
    yield v1.Service()


def parse_mcaffee_webgateway(string_table: v1.type_defs.StringTable) -> Section | None:
    if not string_table:
        return None
    parsed = []
    for index, key, label in (
        (0, "infections", "Infections"),
        (1, "connections_blocked", "Connections blocked"),
    ):
        try:
            parsed.append((key, int(string_table[0][index]), label))
        except (IndexError, ValueError):
            pass
    return parsed


def check_mcafee_webgateway(params: Params, section: Section) -> v1.type_defs.CheckResult:
    now = time.time()
    for key, value, label in section:
        rate = v1.get_rate(v1.get_value_store(), "check_mcafee_webgateway.%s" % key, now, value)
        yield from v1.check_levels(
            rate,
            metric_name="%s_rate" % key,
            levels_upper=params.get(key),
            render_func=lambda f: "%.1f/s" % f,
            label=label,
        )


v1.register.snmp_section(
    name="mcafee_webgateway",
    detect=v1.contains(".1.3.6.1.2.1.1.1.0", "mcafee web gateway"),
    parse_function=parse_mcaffee_webgateway,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.2.1",
        oids=[
            "2",  # MCAFEE-MWG-MIB::stMalwareDetected.0
            "5",  # MCAFEE-MWG-MIB::stConnectionsBlocked.0
        ],
    ),
)

v1.register.check_plugin(
    name="mcafee_webgateway",
    discovery_function=discover_mcafee_gateway,
    check_function=check_mcafee_webgateway,
    service_name="Web gateway statistics",
    check_ruleset_name="mcafee_web_gateway",
    check_default_parameters=Params(),
)
