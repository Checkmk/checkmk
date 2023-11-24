#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import CustomUnit, Localizable


def test_custom_unit_error() -> None:
    title = Localizable("")
    with pytest.raises(ValueError):
        CustomUnit(title, "")
