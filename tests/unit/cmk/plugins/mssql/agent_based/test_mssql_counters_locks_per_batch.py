#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import MutableMapping
from typing import Any

from cmk.agent_based.v2 import Metric, Result
from cmk.plugins.mssql.agent_based.mssql_counters_locks_per_batch import _check_base


def test_check_base_rate_computation() -> None:
    value_store: MutableMapping[str, Any] = {}
    item = "MSSQL_VEEAMSQL2012"

    # First call initializes the rates
    list(
        _check_base(
            value_store,
            item,
            {},
            {
                ("MSSQL_VEEAMSQL2012:SQL_Statistics", "None"): {
                    "batch_requests/sec": 22476651,
                    "forced_parameterizations/sec": 0,
                    "auto-param_attempts/sec": 1133,
                    "failed_auto-params/sec": 1027,
                    "safe_auto-params/sec": 8,
                    "unsafe_auto-params/sec": 98,
                    "sql_compilations/sec": 2189403,
                    "sql_re-compilations/sec": 272134,
                    "sql_attention_rate": 199,
                    "guided_plan_executions/sec": 0,
                    "misguided_plan_executions/sec": 0,
                },
                ("MSSQL_VEEAMSQL2012:Locks", "_Total"): {
                    "lock_requests/sec": 3900449701,
                    "lock_timeouts/sec": 86978,
                    "number_of_deadlocks/sec": 19,
                    "lock_waits/sec": 938,
                    "lock_wait_time_(ms)": 354413,
                    "average_wait_time_(ms)": 354413,
                    "average_wait_time_base": 938,
                    "lock_timeouts_(timeout_>_0)/sec": 0,
                },
            },
            0.0,
        )
    )

    # Second call with incremented counters
    results = list(
        _check_base(
            value_store,
            item,
            {},
            {
                ("MSSQL_VEEAMSQL2012:SQL_Statistics", "None"): {
                    "batch_requests/sec": 22476652,
                    "forced_parameterizations/sec": 0,
                    "auto-param_attempts/sec": 1133,
                    "failed_auto-params/sec": 1027,
                    "safe_auto-params/sec": 8,
                    "unsafe_auto-params/sec": 98,
                    "sql_compilations/sec": 2189403,
                    "sql_re-compilations/sec": 272134,
                    "sql_attention_rate": 199,
                    "guided_plan_executions/sec": 0,
                    "misguided_plan_executions/sec": 0,
                },
                ("MSSQL_VEEAMSQL2012:Locks", "_Total"): {
                    "lock_requests/sec": 3900449702,
                    "lock_timeouts/sec": 86978,
                    "number_of_deadlocks/sec": 19,
                    "lock_waits/sec": 938,
                    "lock_wait_time_(ms)": 354413,
                    "average_wait_time_(ms)": 354413,
                    "average_wait_time_base": 938,
                    "lock_timeouts_(timeout_>_0)/sec": 0,
                },
            },
            60.0,
        )
    )
    assert any(isinstance(r, Result) and "1.0" in r.summary for r in results)
    assert any(isinstance(r, Metric) and r.name == "locks_per_batch" for r in results)
