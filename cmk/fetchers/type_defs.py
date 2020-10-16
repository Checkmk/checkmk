#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

import enum

__all__ = ["Mode"]


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
