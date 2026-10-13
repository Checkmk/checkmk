#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing_engine._operations import (
    op_difference,
    op_fraction,
    op_product,
    op_sum,
    Operator,
)


@pytest.mark.parametrize(
    "operator",
    [
        pytest.param(op_sum, id="sum"),
        pytest.param(op_product, id="product"),
        pytest.param(op_difference, id="difference"),
        pytest.param(op_fraction, id="fraction"),
    ],
)
def test_an_operation_without_a_present_value_has_no_value(operator: Operator) -> None:
    assert operator([None, None]) is None


def test_a_sum_folds_the_present_values() -> None:
    assert op_sum([None, 3.0, 4.0]) == 7.0
