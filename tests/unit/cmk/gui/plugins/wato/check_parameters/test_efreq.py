#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_parameters.efreq import _parameter_valuespec_efreq


@pytest.mark.parametrize(
    "value",
    [
        pytest.param({}, id="both levels omitted"),
        pytest.param({"levels_lower": (45, 40)}, id="lower only, integer values"),
        pytest.param({"levels_upper": (55, 60)}, id="upper only, integer values"),
        pytest.param(
            {"levels_lower": (45, 40), "levels_upper": (55, 60)}, id="both, integer values"
        ),
        pytest.param(
            {"levels_lower": (49.0, 48.5), "levels_upper": (51.0, 51.5)},
            id="both, fractional values",
        ),
    ],
)
def test_efreq_levels_are_optional(value: dict[str, object]) -> None:
    # Both levels_lower and levels_upper are optional keys, so any combination validates.
    # Integer values must keep validating too (allow_int=True) for backwards compatibility.
    _parameter_valuespec_efreq().validate_value(value, "")
