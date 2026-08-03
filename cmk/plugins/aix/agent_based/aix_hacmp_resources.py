#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# <<<aix_hacmp_resources:sep(58)>>>
# pdb213rg:ONLINE:pasv0450:non-concurrent:OHN:FNPN:NFB:ignore::: : :::
# pdb213rg:OFFLINE:pasv0449:non-concurrent:OHN:FNPN:NFB:ignore::: : :::
# pmon01rg:ONLINE:pasv0449:non-concurrent:OHN:FNPN:NFB:ignore::: : :::
# pmon01rg:OFFLINE:pasv0450:non-concurrent:OHN:FNPN:NFB:ignore::: : :::

# parsed =
# {u'pdb213rg': [(u'pasv0450', u'online'), (u'pasv0449', u'offline')],
#  u'pmon01rg': [(u'pasv0449', u'online'), (u'pasv0450', u'offline')]}


import contextlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def parse_aix_hacmp_resources(
    string_table: StringTable,
) -> dict[str, list[tuple[str, str]]]:
    parsed: dict[str, list[tuple[str, str]]] = {}
    for line in string_table:
        joined_line = " ".join(line)
        if (
            "There is no cluster definition" in joined_line
            or "Status of the RSCT subsystems" in joined_line
        ):
            continue
        with contextlib.suppress(IndexError):
            parsed.setdefault(line[0], []).append((line[2], line[1].lower()))
    return parsed


def discover_aix_hacmp_resources(section: dict[str, list[tuple[str, str]]]) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_aix_hacmp_resources(
    item: str, params: Mapping[str, Any], section: dict[str, list[tuple[str, str]]]
) -> CheckResult:
    if not (data := section.get(item)):
        return
    expected_behaviour = params.get("expect_online_on", "first")

    resource_states = []
    infotext = []
    for node_name, resource_state in data:
        resource_states.append(resource_state)
        infotext.append(f"{resource_state} on node {node_name}")

    state = State.OK
    if (expected_behaviour == "first" and resource_states[0] != "online") or (
        expected_behaviour == "any"
        and not any(resource_state == "online" for resource_state in resource_states)
    ):
        state = State.CRIT

    yield Result(state=state, summary=", ".join(infotext))


agent_section_aix_hacmp_resources = AgentSection(
    name="aix_hacmp_resources",
    parse_function=parse_aix_hacmp_resources,
)


check_plugin_aix_hacmp_resources = CheckPlugin(
    name="aix_hacmp_resources",
    service_name="HACMP RG %s",
    discovery_function=discover_aix_hacmp_resources,
    check_function=check_aix_hacmp_resources,
    check_ruleset_name="hacmp_resources",
    check_default_parameters={
        "expect_online_on": "first",
    },
)
