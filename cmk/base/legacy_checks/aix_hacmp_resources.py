#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<aix_hacmp_resources:sep(58)>>>
# pdb213rg:ONLINE:pasv0450:non-concurrent:OHN:FNPN:NFB:ignore::: : :::
# pdb213rg:OFFLINE:pasv0449:non-concurrent:OHN:FNPN:NFB:ignore::: : :::
# pmon01rg:ONLINE:pasv0449:non-concurrent:OHN:FNPN:NFB:ignore::: : :::
# pmon01rg:OFFLINE:pasv0450:non-concurrent:OHN:FNPN:NFB:ignore::: : :::

# parsed =
# {u'pdb213rg': [(u'pasv0450', u'online'), (u'pasv0449', u'offline')],
#  u'pmon01rg': [(u'pasv0449', u'online'), (u'pasv0450', u'offline')]}


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_aix_hacmp_resources(string_table):
    parsed = {}
    for line in string_table:
        joined_line = " ".join(line)
        if (
            "There is no cluster definition" in joined_line
            or "Status of the RSCT subsystems" in joined_line
        ):
            continue
        try:
            parsed.setdefault(line[0], []).append((line[2], line[1].lower()))
        except IndexError:
            pass
    return parsed


def discover_aix_hacmp_resources(parsed):
    return [(key, None) for key in parsed]


def check_aix_hacmp_resources(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    if params is None:
        expected_behaviour = "first"
    else:
        expected_behaviour = params.get("expect_online_on", "first")

    resource_states = []
    infotext = []
    for node_name, resource_state in data:
        resource_states.append(resource_state)
        infotext.append(f"{resource_state} on node {node_name}")

    state = 0
    if expected_behaviour == "first":
        if resource_states[0] != "online":
            state = 2
    elif expected_behaviour == "any":
        if not any(resource_state == "online" for resource_state in resource_states):
            state = 2

    yield state, ", ".join(infotext)


check_info["aix_hacmp_resources"] = LegacyCheckDefinition(
    name="aix_hacmp_resources",
    parse_function=parse_aix_hacmp_resources,
    service_name="HACMP RG %s",
    discovery_function=discover_aix_hacmp_resources,
    check_function=check_aix_hacmp_resources,
    check_ruleset_name="hacmp_resources",
    check_default_parameters={
        "expect_online_on": "first",
    },
)
