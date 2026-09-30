#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.acme.agent_based import acme_temp


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="Crash report a190d738-9b4d-11f1-a1cd-005056a8b5b9: ValueError",
)
def test_check_acme_temp(monkeypatch: pytest.MonkeyPatch) -> None:
    # Crash group 4888: every check of a discovered temperature sensor crashed
    monkeypatch.setattr(acme_temp, "get_value_store", dict)
    section = acme_temp.parse_acme_temp(
        [
            ["FLX1 TEMP1", "24", "2"],
            ["MAIN CPU CORE0 TEMP", "45", "2"],
        ]
    )
    assert section is not None
    results = list(
        acme_temp.check_acme_temp("MAIN CPU CORE0 TEMP", {}, section)  # type: ignore[arg-type]
    )
    assert Metric("temp", 45.0) in results
    assert Result(state=State.OK, summary="Temperature: 45 °C") in results
