#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ucs_bladecenter.agent_based.ucs_bladecenter_topsystem import (
    check_ucs_bladecenter_topsystem,
    discover_ucs_bladecenter_topsystem,
    parse_ucs_bladecenter_topsystem,
)

# The first element names the class and is skipped, as is any element without a value.
_SECTION = parse_ucs_bladecenter_topsystem(
    [
        [
            "topSystem",
            "Address 172.20.33.175",
            "CurrentTime 2015-07-15T16:40:27.600",
            "Mode cluster",
            "Name svie23ucsfi01",
            "NoValue",
        ]
    ]
)


def test_discover_ucs_bladecenter_topsystem() -> None:
    assert list(discover_ucs_bladecenter_topsystem(_SECTION)) == [Service()]


def test_check_ucs_bladecenter_topsystem() -> None:
    assert list(check_ucs_bladecenter_topsystem(_SECTION)) == [
        Result(state=State.OK, summary="Address: 172.20.33.175"),
        Result(state=State.OK, summary="CurrentTime: 2015-07-15T16:40:27.600"),
        Result(state=State.OK, summary="Mode: cluster"),
        Result(state=State.OK, summary="Name: svie23ucsfi01"),
    ]
