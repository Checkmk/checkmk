#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import zypper


@pytest.mark.parametrize("string_table", [None])
def test_zypper_discover(string_table: zypper.Section) -> None:
    services = list(zypper.discover_zypper(string_table))
    assert len(services) == 1
    assert services[0] == Service()


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            [
                [
                    "ERROR: An error occurred",
                ],
            ],
            [Result(state=State.UNKNOWN, summary="ERROR: An error occurred")],
        ),
        (
            [
                [
                    "0 patches needed. ( 0 security patches )",
                ],
            ],
            [Result(state=State.OK, summary="0 updates")],
        ),
        (
            [
                [
                    "Updates for openSUSE 12.1 12.1-1.4 ",
                    " openSUSE-2012-324 ",
                    " 1       ",
                    " recommended ",
                    " needed ",
                    " util-linux: make mount honor 'noexec' and 'user' option",
                ],
                [
                    "1 ",
                    " apache ",
                    " package ",
                    " (any)",
                ],
                [
                    "2 ",
                    " mysql  ",
                    " package ",
                    " (any)",
                ],
            ],
            [
                Result(state=State.OK, summary="1 updates"),
                Result(state=State.WARN, summary="2 locks"),
                Result(state=State.WARN, notice="recommended: 1"),
            ],
        ),
        (
            [
                [
                    "4 patches needed (2 security patches)",
                ],
                [
                    "SLE11-SDK-SP4-Updates ",
                    " sdksp4-apache2-mod_fcgid-12653 ",
                    " 1       ",
                    " security    ",
                    " needed",
                ],
                [
                    "SLES11-SP4-Updates    ",
                    " slessp4-mysql-12847            ",
                    " 1       ",
                    " security    ",
                    " needed",
                ],
                [
                    "SLES11-SP4-Updates    ",
                    " slessp4-timezone-12844         ",
                    " 1       ",
                    " recommended ",
                    " needed",
                ],
                [
                    "SLES11-SP4-Updates    ",
                    " slessp4-wget-12826             ",
                    " 1       ",
                    " recommended ",
                    " needed",
                ],
            ],
            [
                Result(state=State.OK, summary="4 updates"),
                Result(state=State.WARN, notice="recommended: 2"),
                Result(state=State.CRIT, notice="security: 2"),
            ],
        ),
        (
            [
                [
                    "SLES12-SP1-Updates ",
                    " SUSE-SLE-SERVER-12-SP1-2016-1150 ",
                    " recommended ",
                    " low       ",
                    " ---         ",
                    " needed ",
                    " Recommended update for release-notes-sles# SLES12-SP1-Updates",
                ]
            ],
            [
                Result(state=State.OK, summary="1 updates"),
                Result(state=State.WARN, notice="recommended: 1"),
            ],
        ),
        (
            [
                [
                    "SLES12-SP1-Updates ",
                    " SUSE-SLE-SERVER-12-SP1-2016-1150 ",
                    " not relevant ",
                    " low       ",
                    " ---         ",
                    " needed ",
                    " Recommended update for release-notes-sles# SLES12-SP1-Updates",
                ]
            ],
            [
                Result(state=State.OK, summary="1 updates"),
                Result(state=State.OK, notice="not relevant: 1"),
            ],
        ),
    ],
)
def test_zypper_check(string_table: StringTable, expected_result: CheckResult) -> None:
    section = zypper.parse_zypper(string_table)
    assert list(zypper.check_zypper(zypper.DEFAULT_PARAMS, section)) == expected_result


def test_zypper_check_remapping() -> None:
    # Assemble
    section = zypper.ZypperUpdates(
        patch_types=["security", "recommended", "not relevant"],
        locks=["a lock"],
    )
    params = zypper.Param(
        locks=int(State.OK),
        security=int(State.OK),
        recommended=int(State.OK),
        other=int(State.CRIT),
    )
    # Act
    results = [r for r in zypper.check_zypper(params, section) if isinstance(r, Result)]
    # Assert
    for type_ in ("security", "recommended", "locks"):
        patch_states = [r.state for r in results if type_ in r.details]
        assert patch_states == [State.OK]
    assert [r.state for r in results if "not relevant" in r.details] == [State.CRIT]
