#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from types import ModuleType

import pytest

from tests.testlib.unit.utils import import_module_hack


@pytest.fixture(name="check_sql", scope="module")
def fixture_check_sql() -> ModuleType:
    return import_module_hack("active_checks/check_sql")


@pytest.mark.parametrize(
    "result, warn, crit, reference",
    [
        ([[3, "count"]], (3, 5), (float("-inf"), 5), (0, "count: 3.0")),
        ([[2, "count"]], (3, 5), (float("-inf"), 5), (1, "count: 2.0")),
        ([[5, "count"]], (3, 5), (float("-inf"), 5), (2, "count: 5.0")),
        ([[5, "count"]], (3, 5), (float("-inf"), 8), (1, "count: 5.0")),
    ],
)
def test_process_result(
    check_sql: ModuleType,
    result: list,
    warn: tuple[int, int],
    crit: tuple[float, int],
    reference: tuple[int, str],
) -> None:
    assert (
        check_sql.process_result(
            result=result,
            warn=warn,
            crit=crit,
            metrics=None,
            debug=False,
        )
        == reference
    )
