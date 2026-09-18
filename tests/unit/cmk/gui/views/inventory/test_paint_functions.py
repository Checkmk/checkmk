#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.views.inventory._paint_functions import inv_paint_generic
from cmk.gui.views.inventory.registry import PaintResult
from cmk.inventory.structured_data import SDValue


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(True, ("", "Yes"), id="true"),
        pytest.param(False, ("", "No"), id="false"),
        pytest.param(0, ("number", "0"), id="zero"),
        pytest.param(1, ("number", "1"), id="int"),
        pytest.param(1.5, ("number", "1.50"), id="float"),
        pytest.param("text", ("", "text"), id="str"),
        pytest.param("", ("", ""), id="empty-str"),
        pytest.param(None, ("", ""), id="none"),
    ],
)
def test_inv_paint_generic(value: SDValue, expected: PaintResult) -> None:
    assert inv_paint_generic(value) == expected
