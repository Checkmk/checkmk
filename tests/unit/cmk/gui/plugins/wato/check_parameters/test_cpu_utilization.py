#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.plugins.wato.check_parameters.cpu_utilization import _cpu_utilization_to_dict


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            {},
            {},
            id="dict is empty",
        ),
        pytest.param(
            {"levels": (80.0, 90.0)},
            {"util": (80.0, 90.0)},
            id="dict has levels as key",
        ),
        pytest.param(
            (80.0, 90.0),
            {"util": (80.0, 90.0)},
            id="input is tuple",
        ),
        pytest.param(
            {"util": (80.0, 90.0)},
            {"util": (80.0, 90.0)},
            id="dict is already correct",
        ),
        pytest.param(
            {"levels": (80.0, 90.0), "unknown key": "better keep it"},
            {"util": (80.0, 90.0), "unknown key": "better keep it"},
            id="keep additional keys",
        ),
    ],
)
def test_transform(
    entry: tuple[float, float] | dict[str, tuple[float, float]],
    result: Mapping[str, tuple[float, float]],
) -> None:
    assert _cpu_utilization_to_dict(entry) == result
