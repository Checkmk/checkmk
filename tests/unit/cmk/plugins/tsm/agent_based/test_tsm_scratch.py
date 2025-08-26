#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.tsm.agent_based.tsm_scratch import (
    check_tsm_scratch,
    discovery_tsm_scratch,
    parse_tsm_scratch,
    Section,
)


def test_parse_tsm_scratch() -> None:
    parsed = parse_tsm_scratch([["inst", "8", "lib"]])
    assert parsed == {"inst / lib": 8}


def test_discovery_tsm_scratch() -> None:
    services = discovery_tsm_scratch(
        {
            "inst / lib": 8,
        }
    )
    assert list(services) == [Service(item="inst / lib")]


@pytest.mark.parametrize(
    "data, params, expected",
    [
        (
            {
                "inst / lib": 8,
            },
            {"levels_lower": ("fixed", (7, 5))},
            [
                Result(state=State.OK, summary="Found tapes: 8"),
                Metric("tapes_free", 8.0),
            ],
        ),
        (
            {
                "inst / lib": 6,
            },
            {"levels_lower": ("fixed", (7, 5))},
            [
                Result(state=State.WARN, summary="Found tapes: 6 (warn/crit below 7/5)"),
                Metric("tapes_free", 6.0),
            ],
        ),
        (
            {
                "inst / lib": 4,
            },
            {"levels_lower": ("fixed", (7, 5))},
            [
                Result(state=State.CRIT, summary="Found tapes: 4 (warn/crit below 7/5)"),
                Metric("tapes_free", 4.0),
            ],
        ),
        (
            {
                "inst / lib": 4,
            },
            {"levels_lower": ("fixed", (5, 1))},
            [
                Result(state=State.WARN, summary="Found tapes: 4 (warn/crit below 5/1)"),
                Metric("tapes_free", 4.0),
            ],
        ),
        (
            {
                "inst / lib": 4,
            },
            {"levels_lower": None},
            [
                Result(state=State.OK, summary="Found tapes: 4"),
                Metric("tapes_free", 4.0),
            ],
        ),
    ],
)
def test_check_tsm_scratch(data: Section, params: Mapping[str, Any], expected: CheckResult) -> None:
    checked = check_tsm_scratch("inst / lib", params, data)
    assert list(checked) == expected
