#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NamedTuple

from cmk.agent_based.v2 import any_of, equals, State


class VirtualService(NamedTuple):
    name: str
    connections: int | None
    state: State
    state_txt: str
    oid_end: str


VSSection = Mapping[str, VirtualService]

DETECT_KEMP_LOADMASTER = any_of(
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12196.250.10"),
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2021.250.10"),
)
