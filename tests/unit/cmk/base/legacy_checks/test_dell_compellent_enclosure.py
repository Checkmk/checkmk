#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.dell_compellent_enclosure import (
    check_dell_compellent_enclosure,
    parse_dell_compellent_enclosure,
)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {},
            [
                ["1", "1", "", "TYP", "MODEL", "TAG"],
                ["2", "999", "", "TYP", "MODEL", "TAG"],
                ["3", "1", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["4", "999", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["10", "2", "KAPUTT", "TYP", "MODEL", "TAG"],
            ],
            [(0, "Status: UP"), (0, "Model: MODEL, Type: TYP, Service-Tag: TAG")],
        ),
        (
            "2",
            {},
            [
                ["1", "1", "", "TYP", "MODEL", "TAG"],
                ["2", "999", "", "TYP", "MODEL", "TAG"],
                ["3", "1", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["4", "999", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["10", "2", "KAPUTT", "TYP", "MODEL", "TAG"],
            ],
            [(3, "Status: unknown[999]"), (0, "Model: MODEL, Type: TYP, Service-Tag: TAG")],
        ),
        (
            "3",
            {},
            [
                ["1", "1", "", "TYP", "MODEL", "TAG"],
                ["2", "999", "", "TYP", "MODEL", "TAG"],
                ["3", "1", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["4", "999", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["10", "2", "KAPUTT", "TYP", "MODEL", "TAG"],
            ],
            [
                (0, "Status: UP"),
                (0, "Model: MODEL, Type: TYP, Service-Tag: TAG"),
                (0, "State Message: ATTENTION"),
            ],
        ),
        (
            "4",
            {},
            [
                ["1", "1", "", "TYP", "MODEL", "TAG"],
                ["2", "999", "", "TYP", "MODEL", "TAG"],
                ["3", "1", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["4", "999", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["10", "2", "KAPUTT", "TYP", "MODEL", "TAG"],
            ],
            [
                (3, "Status: unknown[999]"),
                (0, "Model: MODEL, Type: TYP, Service-Tag: TAG"),
                (3, "State Message: ATTENTION"),
            ],
        ),
        (
            "10",
            {},
            [
                ["1", "1", "", "TYP", "MODEL", "TAG"],
                ["2", "999", "", "TYP", "MODEL", "TAG"],
                ["3", "1", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["4", "999", "ATTENTION", "TYP", "MODEL", "TAG"],
                ["10", "2", "KAPUTT", "TYP", "MODEL", "TAG"],
            ],
            [
                (2, "Status: DOWN"),
                (0, "Model: MODEL, Type: TYP, Service-Tag: TAG"),
                (2, "State Message: KAPUTT"),
            ],
        ),
    ],
)
def test_check_dell_compellent_enclosure(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for dell_compellent_enclosure check."""
    parsed = parse_dell_compellent_enclosure(string_table)
    result = list(check_dell_compellent_enclosure(item, params, parsed))
    assert result == expected_results
