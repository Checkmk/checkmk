#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Optional

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclass(frozen=True)
class Secondaries:
    active: Optional[str]


@dataclass(frozen=True)
class ReplicaSet:
    primary: Optional[str]
    secondaries: Secondaries
    arbiters: Optional[str]


def parse_mongodb_replica(string_table: StringTable) -> ReplicaSet:
    section_dict = {line[0]: line[1] for line in string_table}
    primary = section_dict.get("primary")
    return ReplicaSet(
        primary=primary if primary != "n/a" else None,
        secondaries=Secondaries(
            active=section_dict.get("hosts"),
        ),
        arbiters=section_dict.get("arbiters"),
    )


register.agent_section(
    name="mongodb_replica",
    parse_function=parse_mongodb_replica,
)


def discover_mongodb_replica(section: ReplicaSet) -> DiscoveryResult:
    yield Service()


def check_mongodb_replica(section: ReplicaSet) -> CheckResult:
    yield (
        Result(
            state=State.OK,
            summary=f"Primary: {section.primary}",
        )
        if section.primary is not None
        else Result(
            state=State.CRIT,
            summary="Replica set does not have a primary node",
        )
    )
    if section.secondaries.active:
        yield Result(
            state=State.OK,
            summary=f"Hosts: {section.secondaries.active}",
        )
    if section.arbiters:
        yield Result(
            state=State.OK,
            summary=f"Arbiters: {section.arbiters}",
        )


register.check_plugin(
    name="mongodb_replica",
    service_name="MongoDB Replica Set Status",
    discovery_function=discover_mongodb_replica,
    check_function=check_mongodb_replica,
)
