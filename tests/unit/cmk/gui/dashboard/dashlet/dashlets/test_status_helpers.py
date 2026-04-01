#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.dashboard.dashlet.dashlets.status_helpers import _purge_unit_spec_for_js
from cmk.gui.graphing._unit import (
    ConvertibleUnitSpecification,
    DecimalNotation,
    IECNotation,
)
from cmk.gui.unit_formatter import AutoPrecision, StrictPrecision
from cmk.gui.utils.temperate_unit import TemperatureUnit


@pytest.mark.parametrize(
    ["unit_spec", "expected_result"],
    [
        pytest.param(
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="Hz"),
                precision=AutoPrecision(digits=3),
            ),
            {
                "unit": {
                    "formatter_type": "DecimalFormatter",
                    "symbol": "Hz",
                    "precision_type": "auto",
                    "precision_digits": 3,
                    "stepping": None,
                },
            },
            id="standard stepping",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=IECNotation(symbol="X"),
                precision=StrictPrecision(digits=2),
            ),
            {
                "unit": {
                    "formatter_type": "IECFormatter",
                    "symbol": "X",
                    "precision_type": "strict",
                    "precision_digits": 2,
                    "stepping": "binary",
                },
            },
            id="binary stepping",
        ),
    ],
)
def test_purge_unit_spec_for_js(
    unit_spec: ConvertibleUnitSpecification, expected_result: Mapping[str, object]
) -> None:
    assert (
        _purge_unit_spec_for_js(unit_spec, temperature_unit=TemperatureUnit.CELSIUS)
        == expected_result
    )
