#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Sequence
from typing import Protocol

import cmk.utils.resulttype as result
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.hostaddress import HostAddress, HostName

from cmk.snmplib import SNMPRawData

from cmk.fetchers import FetcherType

__all__ = ["FetcherFunction", "HostKey", "SourceInfo", "SourceType"]


class SourceType(enum.Enum):
    """Classification of management sources vs regular hosts"""

    HOST = enum.auto()
    MANAGEMENT = enum.auto()


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
    ]:
        ...
