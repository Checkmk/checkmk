#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import metrics, Title


def test_auto_precision_error() -> None:
    with pytest.raises(ValueError):
        metrics.AutoPrecision(-1)


def test_strict_precision_error() -> None:
    with pytest.raises(ValueError):
        metrics.StrictPrecision(-1)


def test_metric_error_empty_name() -> None:
    title = Title("")
    unit = metrics.Unit(metrics.DecimalNotation(""))
    color = metrics.Color.BLUE
    with pytest.raises(ValueError):
        metrics.Metric(name="", title=title, unit=unit, color=color)


def test_warning_of_error_empty_name() -> None:
    with pytest.raises(ValueError):
        metrics.WarningOf("")


def test_critical_of_error_empty_name() -> None:
    with pytest.raises(ValueError):
        metrics.CriticalOf("")


def test_minimum_of_error_empty_name() -> None:
    color = metrics.Color.BLUE
    with pytest.raises(ValueError):
        metrics.MinimumOf("", color)


def test_maximum_of_error_empty_name() -> None:
    color = metrics.Color.BLUE
    with pytest.raises(ValueError):
        metrics.MaximumOf("", color)


def test_sum_error_no_summands() -> None:
    title = Title("Title")
    with pytest.raises(AssertionError):
        metrics.Sum(title, metrics.Color.BLUE, [])


def test_sum_error_segments_empty_name() -> None:
    title = Title("Title")
    color = metrics.Color.BLUE
    with pytest.raises(ValueError):
        metrics.Sum(title, color, [""])


def test_product_error_no_factors() -> None:
    title = Title("Title")
    unit = metrics.Unit(metrics.DecimalNotation(""))
    color = metrics.Color.BLUE
    with pytest.raises(AssertionError):
        metrics.Product(title, unit, color, [])


def test_product_error_factors_empty_name() -> None:
    title = Title("Title")
    unit = metrics.Unit(metrics.DecimalNotation(""))
    color = metrics.Color.BLUE
    with pytest.raises(ValueError):
        metrics.Product(title, unit, color, [""])


def test_difference_error_minuend_empty_name() -> None:
    title = Title("Title")
    color = metrics.Color.BLUE
    subtrahend = "subtrahend"
    with pytest.raises(ValueError):
        metrics.Difference(title, color, minuend="", subtrahend=subtrahend)


def test_difference_error_subtrahend_empty_name() -> None:
    title = Title("Title")
    color = metrics.Color.BLUE
    minuend = "minuend"
    with pytest.raises(ValueError):
        metrics.Difference(title, color, minuend=minuend, subtrahend="")


def test_fraction_error_dividend_empty_name() -> None:
    title = Title("Title")
    unit = metrics.Unit(metrics.DecimalNotation(""))
    color = metrics.Color.BLUE
    divisor = "divisor"
    with pytest.raises(ValueError):
        metrics.Fraction(title, unit, color, dividend="", divisor=divisor)


def test_fraction_error_divisor_empty_name() -> None:
    title = Title("Title")
    unit = metrics.Unit(metrics.DecimalNotation(""))
    color = metrics.Color.BLUE
    dividend = "dividend"
    with pytest.raises(ValueError):
        metrics.Fraction(title, unit, color, dividend=dividend, divisor="")
