#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass
from typing import Optional, Sequence

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclass(frozen=True)
class Secondaries:
    active: Sequence[str]
    passive: Sequence[str]


@dataclass(frozen=True)
class ReplicaSet:
    primary: Optional[str]
    secondaries: Secondaries
    arbiters: Sequence[str]


def _parse_concatenated_hosts(concatenated_hosts: Optional[str]) -> Sequence[str]:
    """
    >>> _parse_concatenated_hosts(None)
    []
    >>> _parse_concatenated_hosts("mongodb1.com")
    ['mongodb1.com']
    >>> _parse_concatenated_hosts("mongodb1.com mongodb2.com mongodb3.com")
    ['mongodb1.com', 'mongodb2.com', 'mongodb3.com']
    """
    if not concatenated_hosts:
        return []
    return concatenated_hosts.split(" ")


def _parse_mongodb_replica_legacy(string_table: StringTable) -> ReplicaSet:
    section_dict = {line[0]: line[1] for line in string_table}
    primary = section_dict.get("primary")
    return ReplicaSet(
        primary=primary if primary != "n/a" else None,
        secondaries=Secondaries(
            active=_parse_concatenated_hosts(section_dict.get("hosts")),
            passive=[],
        ),
        arbiters=_parse_concatenated_hosts(section_dict.get("arbiters")),
    )


def parse_mongodb_replica(string_table: StringTable) -> ReplicaSet:
    if string_table[0][0] == "primary":
        return _parse_mongodb_replica_legacy(string_table)

    section_dict = json.loads(string_table[0][0])
    return ReplicaSet(
        primary=section_dict["primary"],
        secondaries=Secondaries(
            active=section_dict["secondaries"]["active"],
            passive=section_dict["secondaries"]["passive"],
        ),
        arbiters=section_dict["arbiters"],
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
    yield from (
        Result(
            state=State.OK,
            summary=f"{designation.capitalize()}: {', '.join(hosts)}",
        )
        if hosts
        else Result(
            state=State.OK,
            summary=f"No {designation}",
        )
        for designation, hosts in (
            (
                "active secondaries",
                section.secondaries.active,
            ),
            (
                "passive secondaries",
                section.secondaries.passive,
            ),
            (
                "arbiters",
                section.arbiters,
            ),
        )
    )


register.check_plugin(
    name="mongodb_replica",
    service_name="MongoDB Replica Set Status",
    discovery_function=discover_mongodb_replica,
    check_function=check_mongodb_replica,
)
