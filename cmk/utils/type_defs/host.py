#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import NewType

__all__ = [
    "HostAgentConnectionMode",
    "HostName",
    "HostAddress",
    "HostgroupName",
    "HostState",
]

HostAddress = NewType("HostAddress", str)
# Let us be honest here, we do not actually make a difference
# between HostAddress and HostName in our code.
HostName = HostAddress

HostgroupName = str
HostState = int


class HostAgentConnectionMode(enum.Enum):
    PULL = "pull-agent"
    PUSH = "push-agent"
