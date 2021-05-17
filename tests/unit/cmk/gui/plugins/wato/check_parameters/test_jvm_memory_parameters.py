#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Tuple, Union

import pytest

from cmk.gui.plugins.wato.check_parameters.jvm_memory import (
    _transform_legacy_parameters_jvm_memory,)


@pytest.mark.parametrize(
    "parameters, expected_result",
    [
        pytest.param(
            (10., 20.),
            {
                "perc_total": (10.0, 20.0),
            },
            id="super-legacy case",
        ),
        pytest.param(
            {
                "totalheap": (10.0, 20.0),
                "heap": (13.4, 15.9),
                "nonheap": (0.1, 30.),
            },
            {
                "perc_total": (10.0, 20.0),
                "perc_heap": (13.4, 15.9),
                "perc_nonheap": (0.1, 30.),
            },
            id="legacy case",
        ),
        pytest.param(
            {
                "perc_total": (10.0, 20.0),
                "perc_heap": (13.4, 15.9),
                "perc_nonheap": (0.1, 30.),
                "abs_total": (10000, 100000),
                "abs_heap": (20000, 312548),
                "abs_nonheap": (987654, 1002455),
            },
            {
                "perc_total": (10.0, 20.0),
                "perc_heap": (13.4, 15.9),
                "perc_nonheap": (0.1, 30.),
                "abs_total": (10000, 100000),
                "abs_heap": (20000, 312548),
                "abs_nonheap": (987654, 1002455),
            },
            id="up to date case",
        ),
    ],
)
def test_transform_legacy_parameters_jvm_memory(
    parameters: Union[Tuple[float, float], Mapping[str, Tuple[float, float]]],
    expected_result: Mapping[str, Tuple[float, float]],
) -> None:
    assert _transform_legacy_parameters_jvm_memory(parameters) == expected_result
