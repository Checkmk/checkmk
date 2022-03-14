#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.windows_updates import parse_windows_updates, Section

SECTION = Section(
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
)


OUTPUT = """<<<windows_updates>>>
0 2 5
Windows XP Service Pack 3 (KB936929); Windows-Tool zum Entfernen sch�dlicher Software - M�rz 2011 (KB890830)
Update f�r WMDRM-f�hige Medienplayer (KB891122); Windows Media Player 11; Windows Search 4.0 f�r Windows XP (KB940157); Microsoft Base Smartcard-Kryptografiedienstanbieter-Paket: x86 (KB909520); Update f�r die Microsoft .NET Framework 3.5 Service Pack 1- und .NET Framework 3.5-Produktfamilie (KB951847) x86
"""


def test_parse_windows_updates() -> None:
    assert parse_windows_updates([x.split() for x in OUTPUT.splitlines()[1:]]) == SECTION


def test_discover_windows_updates(fix_register) -> None:
    discover_windows_updates = fix_register.check_plugins[
        CheckPluginName("windows_updates")
    ].discovery_function

    assert list(discover_windows_updates(section=SECTION)) == [
        Service(parameters={"auto-migration-wrapper-key": (0, 0, 0, 0, 604800, 172800, True)})
    ]


def test_check_windows_updates(fix_register) -> None:
    check_windows_updates = fix_register.check_plugins[
        CheckPluginName("windows_updates")
    ].check_function
    assert list(
        check_windows_updates(
            params={"auto-migration-wrapper-key": (0, 0, 0, 0, 604800, 172800, True)},
            section=SECTION,
        )
    ) == [
        Result(state=State.CRIT, summary="Important: 2 (warn/crit at 0/0)"),
        Metric("important", 2.0, levels=(0.0, 0.0)),
        Result(
            state=State.OK,
            summary="(Windows XP Service Pack 3 (KB936929); Windows-Tool zum Entfernen sch�dlicher Software - M�rz 2011 (KB890830))",
        ),
        Result(state=State.CRIT, summary="Optional: 5 (warn/crit at 0/0)"),
        Metric("optional", 5.0, levels=(0.0, 0.0)),
    ]
