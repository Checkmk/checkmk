#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator, Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    clusterize,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib import pulse_secure

Section = Mapping[str, int]
CheckOutput = Generator[Result | Metric, None, None]


def parse_pulse_secure_users(string_table: Sequence[StringTable]) -> Section | None:
    try:
        return {"n_users": int(string_table[0][0][0])}
    except IndexError:
        return None
    except ValueError:
        return {}


snmp_section_pulse_secure_users = SNMPSection(
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


def check_pulse_secure_users(params: Mapping[str, Any], section: Section) -> CheckOutput:
    yield from check_levels_v1(
        section["n_users"],
        metric_name="current_users",
        levels_upper=params["upper_number_of_users"],
        label="Pulse Secure users",
        render_func=lambda u: str(int(u)),
    )


def cluster_check_pulse_secure_users(
    params: Mapping[str, Any],
    section: Mapping[str, Section | None],
) -> CheckOutput:
    n_users_total = 0

    for node_name, section_node in section.items():
        if section_node is None:
            continue

        n_users_total += section_node["n_users"]
        yield from clusterize.make_node_notice_results(
            node_name,
            check_pulse_secure_users(
                {"upper_number_of_users": None},
                section_node,
            ),
        )

    yield from check_levels_v1(
        n_users_total,
        metric_name="current_users",
        levels_upper=params["upper_number_of_users"],
        label="Pulse Secure users across cluster",
        render_func=lambda u: str(int(u)),
    )


check_plugin_pulse_secure_users = CheckPlugin(
    name="pulse_secure_users",
    service_name="Pulse Secure users",
    discovery_function=discover_pulse_secure_users,
    check_default_parameters={
        "upper_number_of_users": None,
    },
    check_ruleset_name="pulse_secure_users",
    check_function=check_pulse_secure_users,
    cluster_check_function=cluster_check_pulse_secure_users,
)
