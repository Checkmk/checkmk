#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import Localizable, metrics


def test_physical_unit_error() -> None:
    title = Localizable("")
    with pytest.raises(ValueError):
        metrics.DecimalUnit(title, "")


def test_scientific_unit_error() -> None:
    title = Localizable("")
    with pytest.raises(ValueError):
        metrics.ScientificUnit(title, "")


def test_metric_error_empty_name() -> None:
    title = Localizable("")
    unit = metrics.Unit.COUNT
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
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        metrics.Sum(title, metrics.Color.BLUE, [])


def test_sum_error_segments_empty_name() -> None:
    title = Localizable("Title")
    color = metrics.Color.BLUE
    with pytest.raises(ValueError):
        metrics.Sum(title, color, [""])


def test_product_error_no_factors() -> None:
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        metrics.Product(title, metrics.Unit.COUNT, metrics.Color.BLUE, [])


def test_product_error_factors_empty_name() -> None:
    title = Localizable("Title")
    unit = metrics.Unit.COUNT
    color = metrics.Color.BLUE
    with pytest.raises(ValueError):
        metrics.Product(title, unit, color, [""])


def test_difference_error_minuend_empty_name() -> None:
    title = Localizable("Title")
    color = metrics.Color.BLUE
    subtrahend = "subtrahend"
    with pytest.raises(ValueError):
        metrics.Difference(title, color, minuend="", subtrahend=subtrahend)


def test_difference_error_subtrahend_empty_name() -> None:
    title = Localizable("Title")
    color = metrics.Color.BLUE
    minuend = "minuend"
    with pytest.raises(ValueError):
        metrics.Difference(title, color, minuend=minuend, subtrahend="")


def test_fraction_error_dividend_empty_name() -> None:
    title = Localizable("Title")
    unit = metrics.Unit.COUNT
    color = metrics.Color.BLUE
    divisor = "divisor"
    with pytest.raises(ValueError):
        metrics.Fraction(title, unit, color, dividend="", divisor=divisor)


def test_fraction_error_divisor_empty_name() -> None:
    title = Localizable("Title")
    unit = metrics.Unit.COUNT
    color = metrics.Color.BLUE
    dividend = "dividend"
    with pytest.raises(ValueError):
        metrics.Fraction(title, unit, color, dividend=dividend, divisor="")
