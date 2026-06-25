#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.alcatel.agent_based import alcatel_temp
from cmk.plugins.alcatel.agent_based.alcatel_temp import (
    check_alcatel_temp,
    discover_alcatel_temp,
    parse_alcatel_temp,
)
from cmk.plugins.lib.temperature import TempParamType


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([["29", "0"]], [Service(item="Board")]),
        ([["0", "29"]], [Service(item="CPU")]),
    ],
)
def test_discover_function(info: StringTable, expected_discoveries: Sequence[Service]) -> None:
    parsed_section = parse_alcatel_temp(info)
    result = list(discover_alcatel_temp(parsed_section))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "item, info, expected_state, expected_text",
    [
        ("Slot 1 Board", [["29", "0"]], State.OK, "29.0"),
        ("Slot 1 Board", [["31", "0"]], State.WARN, "31.0"),
        ("Slot 1 Board", [["41", "0"]], State.CRIT, "41.0"),
        ("Slot 1 CPU", [["0", "29"]], State.OK, "29.0"),
        ("Slot 1 CPU", [["0", "31"]], State.WARN, "31.0"),
        ("Slot 1 CPU", [["0", "41"]], State.CRIT, "41.0"),
    ],
)
def test_check_function(
    item: str,
    info: StringTable,
    expected_state: State,
    expected_text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(alcatel_temp, "get_value_store", dict)
    params: TempParamType = {"levels": (30.0, 40.0)}
    parsed_section = parse_alcatel_temp(info)
    results = list(check_alcatel_temp(item, params, parsed_section))
    temp_result = [r for r in results if isinstance(r, Result) and "Temperature" in r.summary][0]
    assert temp_result.state == expected_state
    assert expected_text in temp_result.summary
