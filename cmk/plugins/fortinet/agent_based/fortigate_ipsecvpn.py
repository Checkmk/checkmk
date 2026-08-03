#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fortinet.lib import DETECT_FORTIGATE


def parse_fortigate_ipsecvpn(string_table: StringTable) -> StringTable:
    return string_table


def discover_fortigate_ipsecvpn(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_fortigate_ipsecvpn(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    tunnels_ignore_levels = params["tunnels_ignore_levels"]

    tunnels_down: set[str] = set()
    tunnels_ignored: set[str] = set()
    for p2name, ent_status in section:
        if ent_status == "1":  # down(1), up(2)
            tunnels_down.add(p2name)
            if p2name in tunnels_ignore_levels:
                tunnels_ignored.add(p2name)

    num_total = len(section)
    num_down = len(tunnels_down)
    num_up = num_total - num_down

    num_ignored = len(tunnels_ignored)
    num_down_and_not_ignored = num_down - num_ignored

    infotext = f"Total: {num_total}, Up: {num_up}, Down: {num_down}, Ignored: {num_ignored}"

    warn, crit = params.get("levels", (None, None))
    state = State.OK
    if crit is not None and num_down_and_not_ignored >= crit:
        state = State.CRIT
    elif warn is not None and num_down_and_not_ignored >= warn:
        state = State.WARN
    if state != State.OK:
        infotext += f" (warn/crit at {warn}/{crit})"

    yield Result(state=state, summary=infotext)
    yield Metric("active_vpn_tunnels", num_up, boundaries=(0, num_total))

    long_output: list[str] = []
    for title, tunnels in [
        ("Down and not ignored", sorted(tunnels_down - tunnels_ignored)),
        ("Down", sorted(tunnels_down)),
        ("Ignored", sorted(tunnels_ignored)),
    ]:
        if tunnels:
            long_output.append(f"{title}:")
            long_output.append(", ".join(tunnels))
    if long_output:
        yield Result(state=State.OK, notice="\n".join(long_output))


snmp_section_fortigate_ipsecvpn = SimpleSNMPSection(
    name="fortigate_ipsecvpn",
    detect=DETECT_FORTIGATE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.12.2.2.1",
        oids=["3", "20"],
    ),
    parse_function=parse_fortigate_ipsecvpn,
)

check_plugin_fortigate_ipsecvpn = CheckPlugin(
    name="fortigate_ipsecvpn",
    service_name="VPN IPSec Tunnels",
    discovery_function=discover_fortigate_ipsecvpn,
    check_function=check_fortigate_ipsecvpn,
    check_ruleset_name="ipsecvpn",
    check_default_parameters={
        "tunnels_ignore_levels": [],
        "levels": (1, 2),
    },
)
