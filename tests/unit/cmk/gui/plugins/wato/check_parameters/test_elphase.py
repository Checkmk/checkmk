#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import pytest

from cmk.gui.plugins.wato.check_parameters.elphase import (
    _parameter_valuespec_el_inphase,
    _parameter_valuespec_ups_outphase,
)
from cmk.gui.valuespec import Dictionary


@pytest.mark.parametrize(
    "vs_factory",
    [
        pytest.param(_parameter_valuespec_el_inphase, id="el_inphase"),
        pytest.param(_parameter_valuespec_ups_outphase, id="ups_outphase"),
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        pytest.param({}, id="no levels"),
        pytest.param({"voltage": (210, 200)}, id="lower voltage only"),
        pytest.param({"voltage_upper": (250, 260)}, id="upper voltage only"),
        pytest.param(
            {"voltage": (210, 200), "voltage_upper": (250, 260)},
            id="lower and upper voltage",
        ),
    ],
)
def test_elphase_voltage_upper_is_optional(
    vs_factory: Callable[[], Dictionary], value: dict[str, object]
) -> None:
    # voltage_upper is an optional key, so configuring it (or not) alongside the
    # lower voltage levels must validate.
    vs_factory().validate_value(value, "")
