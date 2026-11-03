#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import Literal

type HostStateLabel = Literal["UP", "DOWN", "UNREACHABLE", "PENDING"]


class HostState(enum.IntEnum):
    UP = 0
    DOWN = 1
    UNREACHABLE = 2
    # Not a real Livestatus state: assigned to a host that has never been checked, whose raw
    # `state` column is meaningless (always 0). See ``LiveStatusHostRepository`` for where this
    # gets constructed instead of the real state.
    PENDING = 3
