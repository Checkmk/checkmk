#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum

__all__ = ["FetcherType"]


class FetcherType(enum.Enum):
    NONE = enum.auto()
    PUSH_AGENT = enum.auto()
    IPMI = enum.auto()
    PIGGYBACK = enum.auto()
    PROGRAM = enum.auto()
    SPECIAL_AGENT = enum.auto()
    SNMP = enum.auto()
    TCP = enum.auto()
