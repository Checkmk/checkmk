#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._parser import parse_unit

from cmk.graphing.v1 import Localizable, PhysicalUnit, ScientificUnit


def test_make_physical_unit_info() -> None:
    unit_info = parse_unit(PhysicalUnit(Localizable("Title"), "symbol"))
    assert unit_info["title"] == "Title"
    assert unit_info["symbol"] == "symbol"
    assert unit_info["render"](0.00024) == "240 µsymbol"
    assert unit_info["js_render"] == "v => cmk.number_format.physical_precision(v, 3, 'symbol')"


def test_make_scientific_unit_info() -> None:
    unit_info = parse_unit(ScientificUnit(Localizable("Title"), "symbol"))
    assert unit_info["title"] == "Title"
    assert unit_info["symbol"] == "symbol"
    assert unit_info["render"](0.00024) == "2.40e-4 symbol"
    assert unit_info["js_render"] == "v => cmk.number_format.scientific(v, 2) + 'symbol'"
