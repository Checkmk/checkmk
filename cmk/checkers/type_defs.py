#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum
from collections.abc import Sequence
from typing import Final, NamedTuple

from cmk.utils.type_defs import HostAddress, HostName, SectionName, SourceType

from cmk.fetchers import FetcherType

__all__ = ["NO_SELECTION", "SectionNameCollection", "SourceInfo", "FetcherType"]


class SourceInfo(NamedTuple):
    hostname: HostName
    ipaddress: HostAddress | None
    ident: str
    fetcher_type: FetcherType
    source_type: SourceType


# Note that the inner Sequence[str] to AgentRawDataSection
# is only **artificially** different from AgentRawData and
# obtained approximatively with `raw_data.decode("utf-8").split()`!
#
# Moreover, the type is not useful.
#
# What would be useful is a Mapping[SectionName, AgentRawData],
# analogous to SNMPRawData = Mapping[SectionName, SNMPRawDataSection],
# that would generalize to `Mapping[SectionName, TRawDataContent]` or
# `Mapping[SectionName, TRawData]` depending on which name we keep.
AgentRawDataSection = Sequence[str]


class SelectionType(enum.Enum):
    NONE = enum.auto()


SectionNameCollection = SelectionType | frozenset[SectionName]
# If preselected sections are given, we assume that we are interested in these
# and only these sections, so we may omit others and in the SNMP case
# must try to fetch them (regardles of detection).

NO_SELECTION: Final = SelectionType.NONE
