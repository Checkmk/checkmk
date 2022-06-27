#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_parameters import domino_tasks


@pytest.mark.parametrize(
    "params, transformed_params",
    [
        (
            {"descr": "abc", "match": "foo", "levels": (1, 2, 3, 4)},
            {"descr": "abc", "match": "foo", "default_params": {"levels": (1, 2, 3, 4)}},
        ),
        (
            {"descr": "abc", "match": "foo", "default_params": {"levels": (1, 2, 3, 4)}},
            {"descr": "abc", "match": "foo", "default_params": {"levels": (1, 2, 3, 4)}},
        ),
    ],
)
def test_transform_discovery_params(params, transformed_params) -> None:
    assert domino_tasks._transform_inv_domino_tasks_rules(params) == transformed_params


@pytest.mark.parametrize(
    "par, result",
    [
        (
            {
                "process": None,
                "warnmin": 1,
                "okmin": 1,
                "okmax": 3,
                "warnmax": 4,
            },
            {
                "process": None,
                "levels": (1, 1, 3, 4),
            },
        ),
        (
            {
                "process": None,
                "levels": (40, 50, 60, 70),
            },
            {
                "process": None,
                "levels": (40, 50, 60, 70),
            },
        ),
    ],
)
def test_transform_valuespec_domino_tasks(par, result) -> None:
    assert domino_tasks._transform_valuespec_domino_tasks(par) == result
