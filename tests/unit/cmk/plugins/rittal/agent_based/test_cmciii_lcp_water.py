#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Service, StringTable
from cmk.plugins.rittal.agent_based.cmciii_lcp_water import (
    check_cmciii_lcp_water,
    discover_cmciii_lcp_water,
    parse_cmciii_lcp_water,
    Section,
)


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [
                ["Luefter_Steuereinheit"],
                ["V09.005"],
                ["V0000"],
                ["OK"],
                ["2"],
                ["Luft_Temperaturen"],
                ["22.1 degree C"],
                ["21.4 degree C"],
                ["19.7 degree C"],
                ["22.5 degree C"],
                ["22.3 degree C"],
                ["21.6 degree C"],
                ["OK"],
                ["2"],
                ["Server_Eintrittstemperatur"],
                ["21.0 degree C"],
                ["21.0 degree C"],
                ["32.0 degree C"],
                ["26.0 degree C"],
                ["12.0 degree C"],
                ["10.0 degree C"],
                ["5 %"],
                ["OK"],
                ["2"],
                ["Server_Austrittstemperatur"],
                ["22.1 degree C"],
                ["45.0 degree C"],
                ["43.0 degree C"],
                ["14.0 degree C"],
                ["12.0 degree C"],
                ["5 %"],
                ["OK"],
                ["2"],
                ["14 %"],
                ["Luefter_1"],
                ["19 %"],
                ["OK"],
                ["2"],
                ["Luefter_2"],
                ["19 %"],
                ["OK"],
                ["2"],
                ["Luefter_3"],
                ["20 %"],
                ["OK"],
                ["2"],
                ["Luefter_4"],
                ["19 %"],
                ["OK"],
                ["2"],
                ["Luefter_5"],
                ["19 %"],
                ["OK"],
                ["2"],
                ["Luefter_6"],
                ["0 %"],
                ["Inactive"],
                ["2"],
                ["Wasser_Steuereinheit"],
                ["V09.002"],
                ["V0000"],
                ["OK"],
                ["2"],
                ["Wasser_Eintrittstemperatur"],
                ["14.8 degree C"],
                ["20.0 degree C"],
                ["17.0 degree C"],
                ["8.0 degree C"],
                ["6.0 degree C"],
                ["5 %"],
                ["OK"],
                ["2"],
                ["Wasser_Austrittstemperatur"],
                ["21.5 degree C"],
                ["35.0 degree C"],
                ["30.0 degree C"],
                ["5.0 degree C"],
                ["3.0 degree C"],
                ["5 %"],
                ["OK"],
                ["2"],
                ["Volumenstrom"],
                ["0.0 l/min"],
                ["130.0 l/min"],
                ["15.0 l/min"],
                ["OK"],
                ["2"],
                ["2-Wege-Regelventil"],
                ["22 %"],
                ["OK"],
                ["2"],
                ["errechnete Kuehlleistung"],
                ["0 W"],
                ["OK"],
                ["2"],
                ["Leckage"],
                ["0"],
                ["OK"],
                ["2"],
                ["Kondensat"],
                ["0"],
                ["0"],
                ["0"],
                ["0 s"],
                ["Off"],
                ["2"],
                ["Automatic"],
                ["Automatic"],
                ["20 %"],
                ["20 %"],
                ["20 %"],
                ["20 %"],
                ["20 %"],
                ["20 %"],
                ["5.0 %"],
                ["Automatic"],
                ["None"],
                ["20 %"],
                ["20 %"],
                ["20 %"],
                ["20 %"],
                ["20 %"],
                ["20 %"],
                ["Automatic"],
                ["None"],
                ["18.8 %"],
            ],
            [],
            id="Missing water measurements do not lead to a crash",
        )
    ],
)
def test_parse_cmciii_lcp_water(string_table: StringTable, section: Section) -> None:
    parsed = parse_cmciii_lcp_water(string_table)
    assert isinstance(parsed, list)
    assert parsed == section


@pytest.mark.parametrize(
    "section, discovered_items",
    [
        pytest.param(
            [],
            [],
            id="Missing water measurements do not lead to a crash",
        )
    ],
)
def test_discover_cmciii_lcp_water(section: Section, discovered_items: Sequence[Service]) -> None:
    assert list(discover_cmciii_lcp_water(section)) == discovered_items


@pytest.mark.parametrize(
    "section, discovered_items",
    [
        pytest.param(
            [],
            [],
            id="Missing water measurements do not lead to a crash",
        )
    ],
)
def test_check_cmciii_lcp_water(section: Section, discovered_items: Sequence[object]) -> None:
    assert list(check_cmciii_lcp_water("bla", {}, section)) == discovered_items
