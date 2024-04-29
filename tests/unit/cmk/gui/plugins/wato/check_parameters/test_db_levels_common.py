#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_parameters.db2_tablespaces import (
    _IEC_UNITS,
    _transform_abs_level_back,
    _transform_abs_level_forth,
)


@pytest.mark.parametrize(
    "iec_unit, expected",
    [
        pytest.param("B", 9.5367431640625e-05, id="bytes"),
        pytest.param("KiB", 0.09765625, id="kibi-bytes"),
        pytest.param("MiB", 100, id="mibi-bytes"),
        pytest.param("GiB", 102400, id="gibi-bytes"),
        pytest.param("TiB", 104857600, id="tebi-bytes"),
    ],
)
def test__transform_abs_level_back(iec_unit: _IEC_UNITS, expected: int | float) -> None:
    assert _transform_abs_level_back((100, iec_unit)) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(9.5367431640625e-05, "B", id="bytes"),
        pytest.param(0.09765625, "KiB", id="kibi-bytes"),
        pytest.param(100, "MiB", id="mibi-bytes"),
        pytest.param(102400, "GiB", id="gibi-bytes"),
        pytest.param(104857600, "TiB", id="tebi-bytes"),
    ],
)
def test__transform_abs_level_forth(value: int | float, expected: _IEC_UNITS) -> None:
    assert _transform_abs_level_forth(value) == (100, expected)
