#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.tsm.rulesets.agent_config_tsm import _migrate


@pytest.mark.parametrize(
    "value,expected",
    [
        # v230p40
        (
            None,
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {"user": "user", "password": "pass", "interval": 300},
            {
                "auth": {
                    "password": ("cmk_postprocesed", "explicit_password", "pass"),
                    "user": "user",
                },
                "deployment": ("cached", 300.0),
            },
        ),
        (
            {"user": "user", "password": "pass"},
            {
                "auth": {
                    "password": ("cmk_postprocesed", "explicit_password", "pass"),
                    "user": "user",
                },
                "deployment": ("sync", None),
            },
        ),
        # incorrectly migrated from v240p16
        (
            {"deployment": ("do_not_deploy", 0.0)},
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {
                "auth": {
                    "password": ("cmk_postprocesed", "explicit_password", "pass"),
                    "user": "user",
                },
                "deployment": ("sync", 300.0),
            },
            {
                "auth": {
                    "password": ("cmk_postprocesed", "explicit_password", "pass"),
                    "user": "user",
                },
                "deployment": ("cached", 300.0),
            },
        ),
        (
            {
                "auth": {
                    "password": ("cmk_postprocesed", "explicit_password", "pass"),
                    "user": "user",
                },
                "deployment": ("cached", None),
            },
            {
                "auth": {
                    "password": ("cmk_postprocesed", "explicit_password", "pass"),
                    "user": "user",
                },
                "deployment": ("sync", None),
            },
        ),
        # v240p16
        (
            {"deployment": ("sync", None), "cmk-match-type": "dict"},
            {"deployment": ("sync", None), "cmk-match-type": "dict"},
        ),
        (
            {"deployment": ("cached", 0.0), "cmk-match-type": "dict"},
            {"deployment": ("cached", 0.0), "cmk-match-type": "dict"},
        ),
        (
            {"deployment": ("do_not_deploy", None), "cmk-match-type": "dict"},
            {"deployment": ("do_not_deploy", None), "cmk-match-type": "dict"},
        ),
        (
            {"cmk-match-type": "dict"},
            {"cmk-match-type": "dict"},
        ),
    ],
)
def test_migrate(value: object, expected: object) -> None:
    migrated = _migrate(value)
    assert migrated == expected
    assert _migrate(migrated) == migrated
