#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.domino.agent_based.domino_info import (
    check_domino_info,
    discover_domino_info,
    parse_domino_info,
)


def test_discover_domino_info_empty() -> None:
    assert list(discover_domino_info([])) == []


def test_discover_domino_info() -> None:
    section: StringTable = [
        ["1", "MEDEMA", "CN=HH-BK4/OU=SRV/O=MEDEMA/C=DE", "Release 8.5.3FP5 HF89"]
    ]
    assert list(discover_domino_info(section)) == [Service()]


def test_check_domino_info() -> None:
    section: StringTable = [
        ["1", "MEDEMA", "CN=HH-BK4/OU=SRV/O=MEDEMA/C=DE", "Release 8.5.3FP5 HF89"]
    ]
    assert list(check_domino_info(parse_domino_info(section))) == [
        Result(state=State.OK, summary="Server is up"),
        Result(state=State.OK, summary="Domain: MEDEMA"),
        Result(
            state=State.OK,
            summary="Name: CN=HH-BK4/OU=SRV/O=MEDEMA/C=DE, Release 8.5.3FP5 HF89",
        ),
    ]


@pytest.mark.xfail(strict=True, reason="Crash group 4521: IndexError on empty section")
def test_check_domino_info_empty_section_does_not_crash() -> None:
    # When the device responds to detection but the data OIDs return nothing,
    # the section ends up empty. The check currently crashes with IndexError.
    assert list(check_domino_info([])) == []
