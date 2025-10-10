#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.alcatel_temp_aos7 import (
    check_alcatel_aos7_temp,
    discover_alcatel_temp_aos7,
    parse_alcatel_aos7_temp,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
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
            ],
            [
                ("CFMA", {}),
                ("CFMB", {}),
                ("CFMC", {}),
                ("CFMD", {}),
                ("CPMA", {}),
                ("CPMB", {}),
                ("FTA", {}),
                ("FTB", {}),
                ("NI1", {}),
                ("NI2", {}),
                ("NI3", {}),
                ("NI4", {}),
                ("NI5", {}),
                ("NI6", {}),
                ("NI7", {}),
                ("NI8", {}),
            ],
        ),
    ],
)
def test_discover_alcatel_temp_aos7(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for alcatel_temp_aos7 check."""

    parsed_section = parse_alcatel_aos7_temp(info)
    result = list(discover_alcatel_temp_aos7(parsed_section))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "CFMA",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "CFMB",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "CFMC",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "CFMD",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "CPMA",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "CPMB",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "FTA",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "FTB",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "NI1",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "NI2",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "NI3",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "NI4",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "NI5",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "NI6",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "NI7",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
        (
            "NI8",
            {"levels": (45, 50)},
            [
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
            ],
            [(0, "44 °C", [("temp", 44, 45, 50)])],
        ),
    ],
)
def test_check_alcatel_temp_aos7(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for alcatel_temp_aos7 check."""

    parsed_section = parse_alcatel_aos7_temp(info)
    result = list(check_alcatel_aos7_temp(item, params, parsed_section))
    assert result == expected_results
