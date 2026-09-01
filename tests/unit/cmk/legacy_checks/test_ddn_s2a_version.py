#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.legacy_checks.ddn_s2a_version import (
    check_ddn_s2a_version,
    discover_ddn_s2a_version,
    parse_ddn_s2a_version,
)

_STRING_TABLE = [
    [
        "0@8@platform@S2A9900@fw_version@6.1.1@fw_date@2013-04-15@bootrom_version@1.2.3@$",
    ],
]


def test_discover_ddn_s2a_version() -> None:
    assert list(discover_ddn_s2a_version(parse_ddn_s2a_version(_STRING_TABLE))) == [Service()]


def test_check_ddn_s2a_version() -> None:
    assert list(check_ddn_s2a_version(parse_ddn_s2a_version(_STRING_TABLE))) == [
        Result(state=State.OK, summary="Platform: S2A9900"),
        Result(state=State.OK, summary="Firmware Version: 6.1.1 (2013-04-15)"),
        Result(state=State.OK, summary="Bootrom Version: 1.2.3"),
    ]
