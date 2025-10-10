#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.base.legacy_checks import juniper_mem_screenos_trpz as juniper_screenos_mem
from cmk.base.legacy_checks.juniper_mem_screenos_trpz import Section


def _section() -> Section:
    """Test data from regression test"""
    return juniper_screenos_mem.parse_juniper_screenos_mem([["157756272", "541531248"]])


def test_discover_juniper_screenos_mem() -> None:
    """Test discovery for juniper_screenos_mem"""
    assert list(juniper_screenos_mem.discover_juniper_mem_generic(_section())) == [
        (None, {}),
    ]


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {"levels": ("perc_used", (80.0, 90.0))},
            (
                0,
                "Used: 22.56% - 150 MiB of 667 MiB",
                [("mem_used", 157756272, 559430016.0, 629358768.0, 0, 699287520)],
            ),
            id="Normal memory usage with percentage levels",
        ),
        pytest.param(
            {"levels": ("perc_used", (20.0, 25.0))},
            (
                1,
                "Used: 22.56% - 150 MiB of 667 MiB (warn/crit at 20.00%/25.00% used)",
                [("mem_used", 157756272, 139857504.0, 174821880.0, 0, 699287520)],
            ),
            id="Memory usage at warning level",
        ),
        pytest.param(
            {"levels": ("perc_used", (15.0, 20.0))},
            (
                2,
                "Used: 22.56% - 150 MiB of 667 MiB (warn/crit at 15.00%/20.00% used)",
                [("mem_used", 157756272, 104893128.0, 139857504.0, 0, 699287520)],
            ),
            id="Memory usage at critical level",
        ),
    ],
)
def test_check_juniper_screenos_mem(
    params: dict[str, Any], expected_result: tuple[int, str, list]
) -> None:
    """Test check function for juniper_screenos_mem"""
    result = juniper_screenos_mem.check_juniper_mem_generic(None, params, _section())
    assert result == expected_result


def test_check_juniper_screenos_mem_missing_item() -> None:
    """Test check function with default parameters"""
    result = juniper_screenos_mem.check_juniper_mem_generic(
        None, {"levels": ("perc_used", (80.0, 90.0))}, _section()
    )
    # Should work the same as normal check since this check uses None as item
    assert result[0] == 0  # Should return OK status
