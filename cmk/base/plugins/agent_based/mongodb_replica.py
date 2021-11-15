#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable


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
