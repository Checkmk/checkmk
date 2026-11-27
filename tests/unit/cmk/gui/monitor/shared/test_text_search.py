#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.shared import contains_wildcard


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("Rack", True, id="text"),
        pytest.param("rack", True, id="ignoring case"),
        pytest.param("Rack*", True, id="trailing star"),
        pytest.param("*1", True, id="leading star"),
        pytest.param("Munich*Rack", True, id="star between parts"),
        pytest.param("Rack*Munich", False, id="parts in the wrong order"),
        pytest.param("Rack.*", False, id="regex characters taken literally"),
        pytest.param("", True, id="empty query"),
    ],
)
def test_contains_wildcard(query: str, expected: bool) -> None:
    assert contains_wildcard("Data center Munich / Rack 1", query) is expected
