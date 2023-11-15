#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import Color, Localizable, metric, Unit


def test_name_error() -> None:
    with pytest.raises(ValueError):
        metric.Name("")


def test_sum_error_no_summands() -> None:
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        metric.Sum(title, Color.BLUE, [])


def test_product_error_no_factors() -> None:
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        metric.Product(title, Unit.COUNT, Color.BLUE, [])
