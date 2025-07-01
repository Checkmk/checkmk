#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Sequence
from typing import Protocol

import cmk.ccc.resulttype as result
from cmk.ccc.cpu_tracking import Snapshot
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.agentdatatype import AgentRawData

from cmk.snmplib import SNMPRawData

__all__ = ["FetcherFunction", "FetcherType", "HostKey", "SourceInfo", "SourceType"]


class SourceType(enum.Enum):
    """Classification of management sources vs regular hosts"""

    HOST = enum.auto()
    MANAGEMENT = enum.auto()


class FetcherType(enum.Enum):
    # TODO(ml): That's too concrete for the engine.  The enum is misplaced.
    #           We'll need a better solution later.  See also CMK-15979.
    NONE = enum.auto()
    PUSH_AGENT = enum.auto()
    IPMI = enum.auto()
    PIGGYBACK = enum.auto()
    PROGRAM = enum.auto()
    SPECIAL_AGENT = enum.auto()
    SNMP = enum.auto()
    TCP = enum.auto()


@dataclasses.dataclass(frozen=True)
class SourceInfo:
    hostname: HostName
    ipaddress: HostAddress | None
    ident: str
    fetcher_type: FetcherType
    source_type: SourceType


@dataclasses.dataclass(frozen=True)
class HostKey:
    hostname: HostName
    source_type: SourceType


class FetcherFunction(Protocol):
    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[
            SourceInfo,
            result.Result[AgentRawData | SNMPRawData, Exception],
            Snapshot,
        ]
    ]: ...
