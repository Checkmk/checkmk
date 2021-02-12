#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum
from typing import List

__all__ = ["AgentSectionContent", "Mode"]

AgentSectionContent = List[List[str]]


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
