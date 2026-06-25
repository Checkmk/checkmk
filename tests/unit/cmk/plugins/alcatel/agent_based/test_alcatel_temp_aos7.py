#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.alcatel.agent_based import alcatel_temp_aos7
from cmk.plugins.alcatel.agent_based.alcatel_temp_aos7 import (
    check_alcatel_aos7_temp,
    discover_alcatel_temp_aos7,
    parse_alcatel_aos7_temp,
)
from cmk.plugins.lib.temperature import TempParamType

_INFO_ALL_44: StringTable = [
    [
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
        "44",
    ]
]


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            _INFO_ALL_44,
            [
                Service(item="CFMA"),
                Service(item="CFMB"),
                Service(item="CFMC"),
                Service(item="CFMD"),
                Service(item="CPMA"),
                Service(item="CPMB"),
                Service(item="FTA"),
                Service(item="FTB"),
                Service(item="NI1"),
                Service(item="NI2"),
                Service(item="NI3"),
                Service(item="NI4"),
                Service(item="NI5"),
                Service(item="NI6"),
                Service(item="NI7"),
                Service(item="NI8"),
            ],
        ),
    ],
)
def test_discover_alcatel_temp_aos7(
    info: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed_section = parse_alcatel_aos7_temp(info)
    result = sorted(discover_alcatel_temp_aos7(parsed_section), key=lambda s: s.item or "")
    assert result == sorted(expected_discoveries, key=lambda s: s.item or "")


_ALL_BOARDS = [
    "CFMA",
    "CFMB",
    "CFMC",
    "CFMD",
    "CPMA",
    "CPMB",
    "FTA",
    "FTB",
    "NI1",
    "NI2",
    "NI3",
    "NI4",
    "NI5",
    "NI6",
    "NI7",
    "NI8",
]


@pytest.mark.parametrize("item", _ALL_BOARDS)
def test_check_alcatel_temp_aos7(item: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(alcatel_temp_aos7, "get_value_store", dict)
    params: TempParamType = {"levels": (45, 50)}
    parsed_section = parse_alcatel_aos7_temp(_INFO_ALL_44)
    results = list(check_alcatel_aos7_temp(item, params, parsed_section))
    assert results == [
        Metric("temp", 44.0, levels=(45.0, 50.0)),
        Result(state=State.OK, summary="Temperature: 44.0 \N{DEGREE SIGN}C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]
