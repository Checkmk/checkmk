#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, MutableMapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Mapping[str, MutableMapping[str, str]]


def parse_lsi(string_table: StringTable) -> Section:
    """Parse lsi section

    >>> parse_lsi([
    ...     ['VolumeID', '2'],
    ...     ['Statusofvolume', 'Okay(OKY)'],
    ...     ['TargetID', '1'],
    ...     ['State', 'Online(ONL)']
    ... ])
    {'arrays': {'2': 'Okay(OKY)'}, 'disks': {'1': 'ONL'}}

    The IDs are considered uniq amongst a host.
    """
    section: Section = {"arrays": {}, "disks": {}}
    iter_st = iter(string_table)
    for (id_type, id_), (_key, state) in zip(iter_st, iter_st):
        if id_type == "VolumeID":
            section["arrays"][id_] = state
        else:
            state = state.split("(")[-1][:-1]
            section["disks"][id_] = state
    return section


def discover_lsi_disk(section: Section) -> DiscoveryResult:
    # Set the discovered state as desired/expected state
    yield from (
        Service(item=item, parameters={"expected_state": value})
        for item, value in section["disks"].items()
    )


def discover_lsi_array(section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section["arrays"])


def check_lsi_array(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    state = section["arrays"].get(item)
    if state is None:
        yield Result(state=State.CRIT, summary="RAID volume %s not existing" % item)
    else:
        yield Result(
            state=State.OK if state == "Okay(OKY)" else State.CRIT, summary=f"Status is '{state}'"
        )


def check_lsi_disk(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    expected_state = params.get("expected_state")
    state = section["disks"].get(item)
    if state is None:
        yield Result(state=State.CRIT, summary="Disk not present")
    elif state == expected_state:
        yield Result(state=State.OK, summary=f"Disk has state '{state}'")
    else:
        yield Result(
            state=State.CRIT, summary=f"Disk has state '{state}' (should be '{expected_state}')"
        )


register.agent_section(
    name="lsi",
    parse_function=parse_lsi,
)

register.check_plugin(
    name="lsi_array",
    sections=["lsi"],
    service_name="RAID array %s",
    discovery_function=discover_lsi_array,
    check_function=check_lsi_array,
    check_default_parameters={},
    # in order to be listed in the enforced service section 'RAID: overall state'.
    check_ruleset_name="raid",
)

register.check_plugin(
    name="lsi_disk",
    sections=["lsi"],
    service_name="RAID disk %s",
    discovery_function=discover_lsi_disk,
    check_function=check_lsi_disk,
    check_default_parameters={},
    check_ruleset_name="raid_disk",
)
