#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.dashboard.dashlet.dashlets.status_helpers import _purge_unit_spec_for_js
from cmk.gui.graphing._formatter import AutoPrecision, StrictPrecision
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation, IECNotation


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
                    "js_render": "v => new cmk.number_format.DecimalFormatter(\n"
                    '    "Hz",\n'
                    "    new cmk.number_format.AutoPrecision(3),\n"
                    ").render(v)",
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
                    "js_render": "v => new cmk.number_format.IECFormatter(\n"
                    '    "X",\n'
                    "    new cmk.number_format.StrictPrecision(2),\n"
                    ").render(v)",
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
    assert _purge_unit_spec_for_js(unit_spec) == expected_result
