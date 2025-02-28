#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerStatus:
    memory: int


@dataclass(frozen=True)
class Shovel:
    name: str
    state: str


@dataclass(frozen=True)
class Queue:
    vhost: str
    name: str
    messages: int


SectionQueues = Mapping[str, Sequence[Queue]]
SectionStatus = Mapping[str, BrokerStatus]
SectionShovels = Mapping[str, Sequence[Shovel]]


_NODE_NAME_PREFIX = "rabbit-"
_NODE_NAME_SUFFIX = "@localhost"


def node_to_site(node_name: str) -> str:
    if not node_name.startswith(_NODE_NAME_PREFIX) or not node_name.endswith(_NODE_NAME_SUFFIX):
        raise ValueError(f"Invalid node name: {node_name}")
    return node_name.removeprefix(_NODE_NAME_PREFIX).removesuffix(_NODE_NAME_SUFFIX)
