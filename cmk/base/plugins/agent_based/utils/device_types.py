#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final
import re
import enum


class SNMPDeviceType(enum.Enum):
    APPLIANCE = enum.auto()
    FIREWALL = enum.auto()
    PRINTER = enum.auto()
    ROUTER = enum.auto()
    SENSOR = enum.auto()
    SWITCH = enum.auto()
    UPS = enum.auto()
    WLC = enum.auto()


_FIBRECHANNEL_MARKER: Final = {"fc", "fibrechannel", "fibre channel"}


def is_fibrechannel_switch(description: str) -> bool:
    return any(m in description.lower() and not re.search(r"fc\d", description.lower())
               for m in _FIBRECHANNEL_MARKER)
