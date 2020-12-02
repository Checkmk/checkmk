#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import Dict, Final, List, Set, Tuple, Union

from cmk.utils.type_defs import SectionName

__all__ = ["SectionCacheInfo", "SectionNameCollection", "NO_SELECTION"]

AgentRawDataSection = List[List[str]]
SectionCacheInfo = Dict[SectionName, Tuple[int, int]]


class SelectionType(enum.Enum):
    NONE = enum.auto()


SectionNameCollection = Union[SelectionType, Set[SectionName]]
# If preselected sections are given, we assume that we are interested in these
# and only these sections, so we may omit others and in the SNMP case (TODO (mo))
# must try to fetch them (regardles of detection).

NO_SELECTION: Final = SelectionType.NONE
