#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest

from tests.testlib import import_module


@pytest.fixture(scope="module")
def check_sql():
    return import_module("active_checks/check_sql")


@pytest.mark.parametrize(
    "result, warn, crit, reference",
    [
        ([[3, "count"]], (3, 5), (float("-inf"), 5), (0, "count: 3.0")),
        ([[2, "count"]], (3, 5), (float("-inf"), 5), (1, "count: 2.0")),
        ([[5, "count"]], (3, 5), (float("-inf"), 5), (2, "count: 5.0")),
        ([[5, "count"]], (3, 5), (float("-inf"), 8), (1, "count: 5.0")),
    ],
)
def test_process_result(check_sql, result, warn, crit, reference) -> None:
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
