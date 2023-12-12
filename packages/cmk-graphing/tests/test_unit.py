#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import Localizable, PhysicalUnit, ScientificUnit


def test_physical_unit_error() -> None:
    title = Localizable("")
    with pytest.raises(ValueError):
        PhysicalUnit(title, "")


def test_scientific_unit_error() -> None:
    title = Localizable("")
    with pytest.raises(ValueError):
        ScientificUnit(title, "")
