#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Protocol

import cmk.ccc.resulttype as result
from cmk.ccc.cpu_tracking import Snapshot
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.helper_interface import AgentRawData, SourceInfo, SourceType
from cmk.snmplib import SNMPRawData

__all__ = ["FetcherFunction", "HostKey"]


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
