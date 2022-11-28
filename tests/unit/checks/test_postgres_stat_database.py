#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.testlib import Check

from cmk.base.api.agent_based.type_defs import StringTable

pytestmark = pytest.mark.checks

CHECK_NAME = "postgres_stat_database.size"


STRING_TABLE = [
    ["[[[main]]]"],
    [
        "datid",
        "datname",
        "numbackends",
        "xact_commit",
        "xact_rollback",
        "blks_read",
        "blks_hit",
        "tup_returned",
        "tup_fetched",
        "tup_inserted",
        "tup_updated",
        "tup_deleted",
        "datsize",
    ],
    ["0", "", "0", "4892", "0", "516", "235823", "111036", "63568", "885", "18", "1", ""],
    [
        "5",
        "postgres",
        "1",
        "2753",
        "9",
        "2487",
        "575988",
        "1440595",
        "323172",
        "23",
        "408",
        "13",
        "7787311",
    ],
    [
        "1",
        "template1",
        "0",
        "2230",
        "0",
        "2745",
        "150164",
        "587296",
        "44020",
        "17515",
        "1158",
        "47",
        "7803695",
    ],
]


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        pytest.param(
            "MAIN/template1",
            {},
            STRING_TABLE,
            [(0, "Size is 7.44 MB", [("size", 7803695)])],
            id="If the database size is available, check result is OK.",
        ),
        pytest.param(
            "MAIN/access_to_shared_objects",
            {},
            STRING_TABLE,
            [(1, "Database size is not available.")],
            id="If the database size is not available, the check result is WARN and a description is provided that the database size is not available.",
        ),
    ],
)
def test_check_postgres_stat_database_size(
    item: str,
    params: Mapping[str, Any],
    section: StringTable,
    expected_result: Sequence[Any],
) -> None:
    size_check = Check(CHECK_NAME)
    main_check = Check("postgres_stat_database")
    assert (
        list(
            size_check.run_check(
                item,
                params,
                main_check.run_parse(section),
            )
        )
        == expected_result
    )
