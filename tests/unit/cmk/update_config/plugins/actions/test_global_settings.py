#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger

from pytest_mock import MockerFixture

from cmk.update_config.plugins.actions import global_settings


def test_update_global_config(mocker: MockerFixture) -> None:
    mocker.patch.object(
        global_settings,
        "_REMOVED_GLOBALS",
        [
            ("global_a", "new_global_a", {True: 1, False: 0}),
            ("global_b", "new_global_b", {}),
            ("missing", "new_missing", {}),
        ],
    )
    mocker.patch.object(
        global_settings,
        "filter_unknown_settings",
        lambda global_config: {k: v for k, v in global_config.items() if k != "unknown"},
    )
    mocker.patch.object(
        global_settings,
        "_transform_global_config_value",
        lambda config_var, config_val: {
            "new_global_a": config_val,
            "new_global_b": 15,
            "global_c": ["x", "y", "z"],
            "unchanged": config_val,
        }[config_var],
    )
    assert global_settings._update_global_config(
        getLogger(),
        {
            "global_a": True,
            "global_b": 14,
            "global_c": None,
            "unchanged": "please leave me alone",
            "unknown": "How did this get here?",
        },
    ) == {
        "global_c": ["x", "y", "z"],
        "unchanged": "please leave me alone",
        "new_global_a": 1,
        "new_global_b": 15,
    }
