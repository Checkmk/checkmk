#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import MutableMapping
from typing import Any

from cmk.agent_based.v2 import Result
from cmk.plugins.mssql.agent_based.mssql_counters_locks import _check_base


def test_check_base_rate_computation() -> None:
    value_store: MutableMapping[str, Any] = {}
    item = "MSSQL_VEEAMSQL2012:Locks _Total lock_requests/sec"

    # First call: initializes rates, emits "Cannot calculate rates yet"
    first_results = list(
        _check_base(
            value_store,
            1597839904,
            item,
            {},
            {
                ("MSSQL_VEEAMSQL2012:Locks", "_Total"): {
                    "lock_requests/sec": 3900449701,
                    "lock_timeouts/sec": 86978,
                    "number_of_deadlocks/sec": 19,
                    "lock_waits/sec": 938,
                    "lock_wait_time_(ms)": 354413,
                },
            },
        )
    )
    assert all(
        "Cannot calculate rates yet" in r.summary for r in first_results if isinstance(r, Result)
    )

    # Second call with incremented counters: produces actual rate results
    second_results = list(
        _check_base(
            value_store,
            1597839905,
            item,
            {},
            {
                ("MSSQL_VEEAMSQL2012:Locks", "_Total"): {
                    "lock_requests/sec": 3900449702,
                    "lock_timeouts/sec": 86979,
                    "number_of_deadlocks/sec": 20,
                    "lock_waits/sec": 939,
                    "lock_wait_time_(ms)": 354413,
                },
            },
        )
    )
    result_summaries = [r.summary for r in second_results if isinstance(r, Result)]
    assert "Requests: 1.0/s" in result_summaries
    assert "Timeouts: 1.0/s" in result_summaries
    assert "Deadlocks: 1.0/s" in result_summaries
    assert "Waits: 1.0/s" in result_summaries
