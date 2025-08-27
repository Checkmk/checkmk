#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import enum

from cmk.ccc.hostaddress import HostAddress, HostName


class SourceType(enum.Enum):
    """Classification of management sources vs regular hosts"""

    HOST = enum.auto()
    MANAGEMENT = enum.auto()


class FetcherType(enum.Enum):
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
