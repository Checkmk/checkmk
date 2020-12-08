#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum
from typing import Dict, Final, List, Set, Tuple, Union

from cmk.utils.type_defs import SectionName

__all__ = ["Mode", "NO_SELECTION", "SectionCacheInfo", "SectionNameCollection"]


class Mode(enum.Enum):
    NONE = enum.auto()
    CHECKING = enum.auto()
    DISCOVERY = enum.auto()
    # Special case of DISCOVERY for the "service discovery page" (automation: try-inventory) which
    # needs to execute the discovery but has to use the available caches, even when dealing with
    # SNMP devices.
    CACHED_DISCOVERY = enum.auto()
    INVENTORY = enum.auto()
    RTC = enum.auto()
    # Special case for discovery/checking/inventory command line argument where we specify in
    # advance all sections we want. Should disable caching, and in the SNMP case also detection.
    # Disabled sections must *not* be discarded in this mode.
    FORCE_SECTIONS = enum.auto()


# Note that the inner List[str] to AgentRawDataSection
# is only **artificially** different from AgentRawData and
# obtained approximatively with `raw_data.decode("utf-8").split()`!
#
# Moreover, the type is not useful.
#
# What would be useful is a Mapping[SectionName, AgentRawData],
# analogous to SNMPRawData = Mapping[SectionName, SNMPRawDataSection],
# that would generalize to `Mapping[SectionName, TRawDataContent]` or
# `Mapping[SectionName, TRawData]` depending on which name we keep.
AgentRawDataSection = List[List[str]]
SectionCacheInfo = Dict[SectionName, Tuple[int, int]]


class SelectionType(enum.Enum):
    NONE = enum.auto()


SectionNameCollection = Union[SelectionType, Set[SectionName]]
# If preselected sections are given, we assume that we are interested in these
# and only these sections, so we may omit others and in the SNMP case (TODO (mo))
# must try to fetch them (regardles of detection).

NO_SELECTION: Final = SelectionType.NONE
