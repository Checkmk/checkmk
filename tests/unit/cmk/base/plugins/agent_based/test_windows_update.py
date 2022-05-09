#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final, Sequence, Union

import pytest
from pytest_mock.plugin import MockerFixture

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.windows_updates import parse_windows_updates, Section

SECTION_OK: Final = Section(
    reboot_required=False,
    important_updates=[
        "Windows XP Service Pack 3 (KB936929)",
        "Windows-Tool zum Entfernen sch�dlicher Software - M�rz 2011 (KB890830)",
    ],
    optional_updates=[
        "Update f�r WMDRM-f�hige Medienplayer (KB891122)",
        "Windows Media Player 11",
        "Windows Search 4.0 f�r Windows XP (KB940157)",
        "Microsoft Base Smartcard-Kryptografiedienstanbieter-Paket: x86 (KB909520)",
        "Update f�r die Microsoft .NET Framework 3.5 Service Pack 1- und .NET"
        " Framework 3.5-Produktfamilie (KB951847) x86",
    ],
    forced_reboot=None,
    failed=None,
)


SECTION_FAILED: Final = Section(
    reboot_required=False,
    important_updates=[],
    optional_updates=[],
    forced_reboot=None,
    failed="The text from the windows_update.vbs, second line!",
)


OUTPUT_OK = """<<<windows_updates>>>
0 2 5
Windows XP Service Pack 3 (KB936929); Windows-Tool zum Entfernen sch�dlicher Software - M�rz 2011 (KB890830)
Update f�r WMDRM-f�hige Medienplayer (KB891122); Windows Media Player 11; Windows Search 4.0 f�r Windows XP (KB940157); Microsoft Base Smartcard-Kryptografiedienstanbieter-Paket: x86 (KB909520); Update f�r die Microsoft .NET Framework 3.5 Service Pack 1- und .NET Framework 3.5-Produktfamilie (KB951847) x86
"""

OUTPUT_FAILED: Final = """<<<windows_updates>>>
x x x
The text from the windows_update.vbs, second line!
"""


def test_parse_windows_updates_ok() -> None:
    assert parse_windows_updates([x.split() for x in OUTPUT_OK.splitlines()[1:]]) == SECTION_OK


def test_parse_windows_updates_failed() -> None:
    assert (
        parse_windows_updates([x.split() for x in OUTPUT_FAILED.splitlines()[1:]]) == SECTION_FAILED
    )


def test_discover_windows_updates(fix_register) -> None:
    discover_windows_updates = fix_register.check_plugins[
        CheckPluginName("windows_updates")
    ].discovery_function
    assert list(discover_windows_updates(section=SECTION_OK)) == [Service()]


@pytest.fixture(name="check_windows_updates")
def check_windows_updates_fixture(fix_register):
    return fix_register.check_plugins[CheckPluginName("windows_updates")].check_function


def test_check_windows_updates_ok(check_windows_updates) -> None:
    assert list(
        check_windows_updates(
            params=dict(
                levels_important=(1, 2),
                levels_optional=(1, 2),
                levels_lower_forced_reboot=(604800, 172800),
            ),
            section=SECTION_OK,
        )
    ) == [
        Result(state=State.CRIT, summary="Important: 2 (warn/crit at 1/2)"),
        Metric("important", 2.0, levels=(1.0, 2.0)),
        Result(
            state=State.OK,
            notice="(Windows XP Service Pack 3 (KB936929); Windows-Tool zum Entfernen sch�dlicher Software - M�rz 2011 (KB890830))",
        ),
        Result(state=State.CRIT, summary="Optional: 5 (warn/crit at 1/2)"),
        Metric("optional", 5.0, levels=(1.0, 2.0)),
    ]


def test_check_windows_updates_failed(check_windows_updates) -> None:
    assert list(
        check_windows_updates(
            params=dict(
                levels_important=(1, 2),
                levels_optional=(1, 2),
                levels_lower_forced_reboot=(604800, 172800),
            ),
            section=SECTION_FAILED,
        )
    ) == [
        Result(state=State.CRIT, summary=f"({SECTION_FAILED.failed})"),
        Result(state=State.OK, summary="Important: 0"),
        Metric("important", 0.0, levels=(1.0, 2.0)),
        Result(state=State.OK, summary="Optional: 0"),
        Metric("optional", 0.0, levels=(1.0, 2.0)),
    ]


def test_reboot_required(check_windows_updates) -> None:
    section = Section(
        reboot_required=True,
        important_updates=[],
        optional_updates=[],
        forced_reboot=None,
        failed=None,
    )
    assert list(
        check_windows_updates(
            params=dict(
                levels_important=None,
                levels_optional=None,
                levels_lower_forced_reboot=(604800, 172800),
            ),
            section=section,
        )
    ) == [
        Result(state=State.OK, summary="Important: 0"),
        Metric("important", 0.0),
        Result(state=State.OK, summary="Optional: 0"),
        Metric("optional", 0.0),
        Result(state=State.WARN, summary="Reboot required to finish updates"),
    ]


@pytest.mark.parametrize(
    "reboot_time, now, results",
    [
        pytest.param(
            3601,
            1,
            [
                Result(state=State.OK, summary="Important: 0"),
                Metric("important", 0.0),
                Result(state=State.OK, summary="Optional: 0"),
                Metric("optional", 0.0),
                Result(state=State.WARN, summary="Reboot required to finish updates"),
                Result(
                    state=State.CRIT,
                    summary="Time to enforced reboot to finish updates: 1 hour 0 minutes (warn/crit below 7 days 0 hours/2 days 0 hours)",
                ),
            ],
            id="report if reboot time is in the future",
        ),
        pytest.param(
            1,
            3601,
            [
                Result(state=State.OK, summary="Important: 0"),
                Metric("important", 0.0),
                Result(state=State.OK, summary="Optional: 0"),
                Metric("optional", 0.0),
                Result(state=State.WARN, summary="Reboot required to finish updates"),
            ],
            id="no report if reboot time is in the past",
        ),
    ],
)
def test_time_until_force_reboot(
    check_windows_updates,
    mocker: MockerFixture,
    reboot_time: float,
    now: float,
    results: Sequence[Union[Result, Metric]],
) -> None:
    mocker.patch("time.time", return_value=now)
    section = Section(
        reboot_required=True,
        important_updates=[],
        optional_updates=[],
        forced_reboot=reboot_time,
        failed=None,
    )
    assert (
        list(
            check_windows_updates(
                params=dict(
                    levels_important=None,
                    levels_optional=None,
                    levels_lower_forced_reboot=(604800, 172800),
                ),
                section=section,
            )
        )
        == results
    )
