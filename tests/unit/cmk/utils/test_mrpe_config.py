#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.utils.mrpe_config import ensure_mrpe_configs, MrpeConfig, MrpeConfigDeprecated


@pytest.mark.parametrize(
    "expected_mrpe_configs, result_mrpe_configs",
    [
        pytest.param(
            [
                (
                    "abc",
                    "/x/y/my-plugin",
                    None,
                ),
                (
                    "ab%20%5Bc%5D%2F%7Bd%7D",
                    "/x/y/my-plugin",
                    {
                        "max_age": 120,
                        "appendage": False,
                    },
                ),
            ],
            [
                {
                    "description": "abc",
                    "cmdline": "/x/y/my-plugin",
                },
                {
                    "description": "ab [c]/{d}",
                    "cmdline": "/x/y/my-plugin",
                    "interval": 120,
                },
            ],
            id="legacy migration",
        ),
        pytest.param(
            [
                {
                    "description": "abc",
                    "cmdline": "/x/y/my-plugin",
                },
                {
                    "description": "ab%20%5Bc%5D%2F%7Bd%7D",
                    "cmdline": "/x/y/my-plugin",
                    "interval": 120,
                },
            ],
            [
                {
                    "description": "abc",
                    "cmdline": "/x/y/my-plugin",
                },
                {
                    "description": "ab%20%5Bc%5D%2F%7Bd%7D",
                    "cmdline": "/x/y/my-plugin",
                    "interval": 120,
                },
            ],
            id="up to date",
        ),
    ],
)
def test_ensure_mrpe_configs(
    expected_mrpe_configs: Sequence[MrpeConfigDeprecated | MrpeConfig],
    result_mrpe_configs: Sequence[MrpeConfig],
) -> None:
    assert ensure_mrpe_configs(expected_mrpe_configs) == result_mrpe_configs
