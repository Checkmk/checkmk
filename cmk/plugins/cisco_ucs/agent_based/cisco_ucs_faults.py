#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2024 SWR
# @author Frank Baier <frank.baier@swr.de>
#
#
from cmk.agent_based.v2 import (
    CheckPlugin,
    Service,
    Result,
    State,
)
from collections.abc import Mapping, Sequence
from cmk.plugins.lib.cisco_ucs import check_cisco_fault, Fault
from cmk.agent_based.v1.type_defs import CheckResult, DiscoveryResult


def discover_cisco_ucs_faults(section: Mapping[str, Sequence[Fault]] | None,) -> DiscoveryResult:
    yield Service()


def check_cisco_ucs_faults(section: Mapping[str, Sequence[Fault]] | None,) -> CheckResult:
    if not section:
        yield Result(state=State.OK, notice="No faults")
        return

    for id, fault in section.items():
        yield from check_cisco_fault(fault)


check_plugin_cisco_ucs_faults = CheckPlugin(
    name="cisco_ucs_faults",
    sections=["cisco_ucs_fault"],
    service_name="Cisco UCS Faults",
    discovery_function=discover_cisco_ucs_faults,
    check_function=check_cisco_ucs_faults,
)
