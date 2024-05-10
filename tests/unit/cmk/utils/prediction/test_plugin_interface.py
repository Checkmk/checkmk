#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.prediction import estimate_levels


def test_estimate_levels_absolute() -> None:
    assert estimate_levels(0, 2, "upper", ("absolute", (2, 4)), None) == (2, 4)


def test_estimate_levels_zero_reference_relative() -> None:
    assert estimate_levels(0, 2, "upper", ("relative", (2, 4)), None) is None


def test_estimate_levels_stdev() -> None:
    assert estimate_levels(0, 2, "upper", ("stdev", (2, 4)), None) == (4, 8)


def test_estimate_levels_stdev_lower() -> None:
    assert estimate_levels(
        15,
        2,
        "lower",
        ("stdev", (3, 5)),
        None,
    ) == (9, 5)


def test_estimate_levels_upper_lbound() -> None:
    assert estimate_levels(42.0, 1.0, "upper", ("stdev", (2.3, 3.2)), None) == (
        44.3,
        45.2,
    )

    assert estimate_levels(42.0, 1.0, "upper", ("stdev", (2.3, 3.2)), (45.0, 45.0)) == (45.0, 45.2)


def test_estimate_levels_lower_ubound() -> None:
    assert estimate_levels(42.0, 1.0, "lower", ("stdev", (2.3, 3.2)), None) == (
        39.7,
        38.8,
    )

    assert estimate_levels(42.0, 1.0, "lower", ("stdev", (2.3, 3.2)), (38.5, 50.0)) == (38.5, 38.8)
