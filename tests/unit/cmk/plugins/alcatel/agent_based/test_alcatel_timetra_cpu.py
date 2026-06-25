#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.alcatel.agent_based import alcatel_timetra_cpu
from cmk.plugins.alcatel.agent_based.alcatel_timetra_cpu import (
    check_alcatel_timetra_cpu,
    discover_alcatel_timetra_cpu,
    parse_alcatel_timetra_cpu,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["92"]], [Service()]),
    ],
)
def test_discover_alcatel_timetra_cpu(
    string_table: StringTable, expected_discoveries: list[Service]
) -> None:
    parsed = parse_alcatel_timetra_cpu(string_table)
    assert parsed is not None
    result = list(discover_alcatel_timetra_cpu(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "params, string_table, expected_state, expected_text",
    [
        (
            {"util": (90.0, 95.0)},
            [["92"]],
            State.WARN,
            "92.00%",
        ),
    ],
)
def test_check_alcatel_timetra_cpu(
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_state: State,
    expected_text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(alcatel_timetra_cpu, "get_value_store", dict)
    parsed = parse_alcatel_timetra_cpu(string_table)
    assert parsed is not None
    results = list(check_alcatel_timetra_cpu(params, parsed))
    result_with_summary = [r for r in results if isinstance(r, Result) and r.summary][0]
    assert result_with_summary.state == expected_state
    assert expected_text in result_with_summary.summary
    metrics = [r for r in results if isinstance(r, Metric)]
    assert any(m.name == "util" for m in metrics)
