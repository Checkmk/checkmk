#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
from statistics import mean
from typing import Dict, List, NamedTuple, Tuple, TypedDict

from .agent_based_api.v1 import (
    all_of,
    check_levels,
    contains,
    exists,
    not_contains,
    OIDEnd,
    register,
    render,
    Service,
    SNMPTree,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.entity_mib import PhysicalClasses

DISCOVERY_DEFAULT_PARAMETERS = {"individual": True, "average": False}


class CPUInfo(NamedTuple):
    util: float


Section = Dict[str, CPUInfo]


class Params(TypedDict):
    levels: Tuple[float, float]


class DiscoveryParams(TypedDict, total=False):
    average: bool
    individual: bool


class Entity(NamedTuple):
    description: str
    physical_class: PhysicalClasses


def parse_cisco_cpu_multiitem(string_table: List[StringTable]) -> Section:
    ph_idx_to_entity: Dict[str, Entity] = {}
    for idx, desc, class_idx in string_table[1]:
        if desc.lower().startswith("cpu "):
            desc = desc[4:]
        ph_idx_to_entity[idx] = Entity(desc, PhysicalClasses.parse_cisco(class_idx))

    parsed = {}
    for cpu_id, idx, util in string_table[0]:
        # if cpmCPUTotalEntry can be referenced to an entPhysicalEntry, use information from there.
        # if cpmCPUTotalEntry has no reference (e.g. is a virtual cpu) use the id of cpmCPUTotalEntry.
        entity = ph_idx_to_entity.get(idx, Entity(cpu_id, PhysicalClasses.unknown))

        if entity.physical_class in {PhysicalClasses.fan, PhysicalClasses.sensor}:
            # in case we have a entPhysicalEntry and see it can not be a cpu, ignore it.
            # we've already seen chassis with cpu (e.g. optional extension slots with cpu)
            continue
        with suppress(ValueError):
            parsed[entity.description] = CPUInfo(util=float(util))

    if values := [data.util for data in parsed.values()]:
        parsed["average"] = CPUInfo(util=mean(values))
    return parsed


def discover_cisco_cpu_multiitem(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    if params["individual"]:
        for item in section:
            if item == "average":
                continue
            yield Service(item=item)
    if params["average"]:
        yield Service(item="average")


def check_cisco_cpu_multiitem(item: str, params: Params, section: Section) -> CheckResult:
    if item not in section:
        return None
    yield from check_levels(
        section[item].util,
        levels_upper=params["levels"],
        metric_name="util",
        render_func=render.percent,
        boundaries=(0, 100),
        label="Utilization in the last 5 minutes",
    )


register.snmp_section(
    name="cisco_cpu_multiitem",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        not_contains(".1.3.6.1.2.1.1.1.0", "nx-os"),
        exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*"),
    ),
    parse_function=parse_cisco_cpu_multiitem,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.109.1.1.1.1",
            oids=[
                OIDEnd(),  # OID index
                "2",  # cpmCPUTotalPhysicalIndex
                "8",  # cpmCPUTotal5minRev
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[
                OIDEnd(),  # OID index
                "7",  # entPhysicalName
                "5",  # entPhysicalClass
            ],
        ),
    ],
)


register.check_plugin(
    name="cisco_cpu_multiitem",
    service_name="CPU utilization %s",
    discovery_function=discover_cisco_cpu_multiitem,
    discovery_default_parameters=DISCOVERY_DEFAULT_PARAMETERS,
    discovery_ruleset_name="cpu_utilization_multiitem_discovery",
    check_default_parameters={"levels": (80.0, 90.0)},
    check_ruleset_name="cpu_utilization_multiitem",
    check_function=check_cisco_cpu_multiitem,
)
