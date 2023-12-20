#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Mapping
from typing import Any

import pytest

from cmk.utils.hostaddress import HostName
from cmk.utils.prediction import _plugin_interface


def test_prediction_updater_serializable() -> None:
    """Make sure the PredictionUpdater is (de)serializable (for automation calls)

    We do not care what it is deserialized to.
    """

    def unserializable_callback(*args: object) -> Any:
        return None

    # this is expected to fail:
    with pytest.raises(SyntaxError):
        _ = ast.literal_eval(repr(unserializable_callback))

    # yet this must work
    _ = ast.literal_eval(
        repr(
            _plugin_interface.PredictionUpdater(
                HostName("myhost"),
                "My service description",
                None,  # type: ignore[arg-type]  # keep the test simple.
                unserializable_callback,
            )
        )
    )


@pytest.mark.parametrize(
    "reference_value, reference_deviation, params, levels_factor, result",
    [
        (
            5,
            2,
            {"levels_lower": ("absolute", (2, 4))},
            1,
            (None, None, 3, 1),
        ),
        (
            0,
            2,
            {"levels_upper": ("absolute", (2, 4))},
            1,
            (2, 4, None, None),
        ),
        (
            0,
            2,
            {"levels_upper": ("relative", (2, 4))},
            1,
            (None, None, None, None),
        ),
        (
            0,
            2,
            {"levels_upper": ("stdev", (2, 4))},
            1,
            (4, 8, None, None),
        ),
        (
            15,
            2,
            {
                "levels_upper": ("stdev", (2, 4)),
                "levels_lower": ("stdev", (3, 5)),
            },
            1,
            (19, 23, 9, 5),
        ),
        (
            2,
            3,
            {
                "levels_upper": ("relative", (20, 40)),
                "levels_upper_min": (2, 4),
            },
            1,
            (2.4, 4, None, None),
        ),
    ],
)
def test_estimate_levels(
    reference_value: float,
    reference_deviation: float,
    params: Mapping,
    levels_factor: float,
    result: _plugin_interface.EstimatedLevels,
) -> None:
    assert (
        _plugin_interface.estimate_levels(
            reference_value=reference_value,
            stdev=reference_deviation,
            levels_lower=params.get("levels_lower"),
            levels_upper=params.get("levels_upper"),
            levels_upper_lower_bound=params.get("levels_upper_min"),
            levels_factor=levels_factor,
        )
        == result
    )
