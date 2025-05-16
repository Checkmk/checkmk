#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.multipath import (
    check_multipath,
    discover_multipath,
    parse_multipath,
)
from cmk.plugins.lib.multipath import Section

STRING_TABLE: Final = [
    ["ORA_ZAPPL2T_DATA_3", "(3600601604d40310047cf93ce66f7e111)", "dm-67", "DGC,RAID", "5"],
    ["size=17G", "features='1", "queue_if_no_path'", "hwhandler='1", "alua'", "wp=rw"],
    ["|-+-", "policy='round-robin", "0'", "prio=0", "status=active"],
    ["| |-", "3:0:1:54", "sddz", "128:16 ", "active", "undef", "running"],
    ["|", "`-", "5:0:1:54", "sdkb", "65:496", "active", "undef", "running"],
    ["`-+-", "policy='round-robin", "0'", "prio=0", "status=enabled"],
    ["|-", "5:0:0:54", "sdbd", "67:112", "active", "undef", "running"],
    ["`-", "3:0:0:54", "sdhf", "133:80", "active", "undef", "running"],
    ["ORA_UC41T_OLOG_1", "(prefix.3600601604d403100912ab0b365f7e111)", "dm-112", "DGC,RAID", "5"],
    ["size=17G features='1 queue_if_no_path' hwhandler='1 alua' wp=rw"],
    ["|-+-", "policy='round-robin", "0'", "prio=0", "status=active"],
    ["|", "|-", "5:0:0:77", "sdew", "129:128", "active", "undef", "running"],
    # broken paths:
    [
        "BROKEN_PATH",
        "(broken_paths)",
        "dm-67",
        "DGC,RAID",
        "5",
    ],
    ["size=17G", "features='1", "queue_if_no_path'", "hwhandler='1", "alua'", "wp=rw"],
    ["|-+-", "policy='round-robin", "0'", "prio=0", "status=active"],
    ["|-", "5:0:0:54", "sdbd", "67:112", "broken", "undef", "running"],
    ["`-", "3:0:0:54", "sdhf", "133:80", "broken", "undef", "running"],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section:
    return parse_multipath(STRING_TABLE)


def test_discovery(section: Section) -> None:
    assert sorted(discover_multipath({"use_alias": False}, section)) == [
        Service(item="3600601604d40310047cf93ce66f7e111", parameters={"levels": 4}),
        Service(item="broken_paths", parameters={"levels": 2}),
        Service(item="prefix.3600601604d403100912ab0b365f7e111", parameters={"levels": 1}),
    ]


def test_check_percent_levels(section: Section) -> None:
    assert list(
        check_multipath(
            "3600601604d40310047cf93ce66f7e111",
            # lower levels. these make no sense, but we want to see a WARN.
            {"levels": (110.0, 40.0)},
            section,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="(ORA_ZAPPL2T_DATA_3): Paths active: 100.00% (warn/crit below 110.00%/40.00%)",
        ),
        Result(
            state=State.OK,
            summary="4 of 4",
        ),
    ]


def test_check_count_levels(section: Section) -> None:
    assert list(
        check_multipath(
            "3600601604d40310047cf93ce66f7e111",
            {"levels": 3},
            section,
        )
    ) == [
        Result(
            state=State.OK,
            summary="(ORA_ZAPPL2T_DATA_3): Paths active: 100.00%",
        ),
        Result(
            state=State.WARN,
            summary="4 of 4 (expected: 3)",
        ),
    ]


def test_check_broken_paths(section: Section) -> None:
    assert list(
        check_multipath(
            "broken_paths",
            {},
            section,
        )
    )[-1] == Result(
        state=State.CRIT,
        summary="Broken paths: 5:0:0:54(sdbd),3:0:0:54(sdhf)",
    )
