#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Generator, List, Mapping, Union
from .agent_based_api.v1 import (
    check_levels,
    clusterize,
    Metric,
    register,
    Result,
    Service,
    SNMPTree,
    type_defs,
)
from .utils import pulse_secure

Section = Mapping[str, int]
CheckOutput = Generator[Union[Result, Metric], None, None]


def parse_pulse_secure_users(string_table: List[type_defs.StringTable]) -> Section:
    raw_data = string_table[0][0][0]
    try:
        return {'n_users': int(raw_data)}
    except ValueError:
        return {}


register.snmp_section(
    name="pulse_secure_users",
    parse_function=parse_pulse_secure_users,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12532",
            oids=[
                "2",  # signedInWebUsers
            ],
        ),
    ],
    detect=pulse_secure.DETECT_PULSE_SECURE,
)


def discover_pulse_secure_users(section: Section) -> Generator[Service, None, None]:
    if section:
        yield Service()


def check_pulse_secure_users(params: type_defs.Parameters, section: Section) -> CheckOutput:
    yield from check_levels(
        section["n_users"],
        metric_name="current_users",
        levels_upper=params.get("upper_number_of_users"),
        label="Pulse Secure users",
        render_func=lambda u: str(int(u)),
    )


def cluster_check_pulse_secure_users(
    params: type_defs.Parameters,
    section: Mapping[str, Section],
) -> CheckOutput:

    n_users_total = 0

    for node_name, section_node in section.items():
        n_users_total += section_node['n_users']
        node_state, node_text = clusterize.aggregate_node_details(
            node_name,
            check_pulse_secure_users(
                type_defs.Parameters({}),
                section_node,
            ),
        )
        if node_text:
            yield Result(state=node_state, notice=node_text)

    yield from check_levels(
        n_users_total,
        metric_name="current_users",
        levels_upper=params.get("upper_number_of_users"),
        label="Pulse Secure users across cluster",
        render_func=lambda u: str(int(u)),
    )


register.check_plugin(
    name="pulse_secure_users",
    service_name="Pulse Secure users",
    discovery_function=discover_pulse_secure_users,
    check_default_parameters={},
    check_ruleset_name="pulse_secure_users",
    check_function=check_pulse_secure_users,
    cluster_check_function=cluster_check_pulse_secure_users,
)
