#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.legacy_bakery_rulesets.nginx_status import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            ("autodetect", [443]),
            {"deployment": ("sync", None), "instances": ("autodetect", [443])},
            id="old_autodetect",
        ),
        pytest.param(
            ("static", [{"protocol": "http", "address": "127.0.0.1", "port": 80}]),
            {
                "deployment": ("sync", None),
                "instances": ("static", [{"protocol": "http", "address": "127.0.0.1", "port": 80}]),
            },
            id="old_static",
        ),
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="old_do_not_deploy",
        ),
        pytest.param(
            (None, None),
            {"deployment": ("do_not_deploy", None)},
            id="old_tuple_none_mode",
        ),
        pytest.param(
            {"deployment": ("sync", None), "instances": ("autodetect", [443])},
            {"deployment": ("sync", None), "instances": ("autodetect", [443])},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
