#  !/usr/bin/env python3
#  Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.rulesets.v1 import FixedValue, Localizable


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(True, id="bool"),
        pytest.param(0, id="int"),
        pytest.param(2.0, id="float"),
        pytest.param("value", id="float"),
        pytest.param(None, id="None"),
    ],
)
def test_fixed_value_validation(
    value: int | float | str | bool | None,
) -> None:
    FixedValue(value=value, title=Localizable("Test FixedValue"))


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(float("Inf"), id="Inf float"),
    ],
)
def test_fixed_value_validation_fails(value: int | float | str | bool | None) -> None:
    with pytest.raises(ValueError, match="FixedValue value is not serializable."):
        FixedValue(value=value, title=Localizable("Test FixedValue"))
