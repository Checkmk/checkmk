#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import Color, Localizable, metric, Unit


def test_metric_error_empty_name() -> None:
    title = Localizable("")
    unit = Unit.COUNT
    color = Color.BLUE
    with pytest.raises(ValueError):
        metric.Metric(name="", title=title, unit=unit, color=color)


def test_warning_of_error_empty_name() -> None:
    with pytest.raises(ValueError):
        metric.WarningOf("")


def test_critical_of_error_empty_name() -> None:
    with pytest.raises(ValueError):
        metric.CriticalOf("")


def test_minimum_of_error_empty_name() -> None:
    color = Color.BLUE
    with pytest.raises(ValueError):
        metric.MinimumOf("", color)


def test_maximum_of_error_empty_name() -> None:
    color = Color.BLUE
    with pytest.raises(ValueError):
        metric.MaximumOf("", color)


def test_sum_error_no_summands() -> None:
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        metric.Sum(title, Color.BLUE, [])


def test_sum_error_segments_empty_name() -> None:
    title = Localizable("Title")
    color = Color.BLUE
    with pytest.raises(ValueError):
        metric.Sum(title, color, [""])


def test_product_error_no_factors() -> None:
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        metric.Product(title, Unit.COUNT, Color.BLUE, [])


def test_product_error_factors_empty_name() -> None:
    title = Localizable("Title")
    unit = Unit.COUNT
    color = Color.BLUE
    with pytest.raises(ValueError):
        metric.Product(title, unit, color, [""])


def test_difference_error_minuend_empty_name() -> None:
    title = Localizable("Title")
    color = Color.BLUE
    subtrahend = "subtrahend"
    with pytest.raises(ValueError):
        metric.Difference(title, color, minuend="", subtrahend=subtrahend)


def test_difference_error_subtrahend_empty_name() -> None:
    title = Localizable("Title")
    color = Color.BLUE
    minuend = "minuend"
    with pytest.raises(ValueError):
        metric.Difference(title, color, minuend=minuend, subtrahend="")


def test_fraction_error_dividend_empty_name() -> None:
    title = Localizable("Title")
    unit = Unit.COUNT
    color = Color.BLUE
    divisor = "divisor"
    with pytest.raises(ValueError):
        metric.Fraction(title, unit, color, dividend="", divisor=divisor)


def test_fraction_error_divisor_empty_name() -> None:
    title = Localizable("Title")
    unit = Unit.COUNT
    color = Color.BLUE
    dividend = "dividend"
    with pytest.raises(ValueError):
        metric.Fraction(title, unit, color, dividend=dividend, divisor="")
