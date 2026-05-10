#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.sap.rulesets.mk_saprouter import migrate


@pytest.mark.parametrize(
    "old_value, expected",
    [
        (
            None,
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {"user": "saprouter", "path": "/usr/sap/sapgenpse"},
            {"deployment": ("sync", None), "user": "saprouter", "path": "/usr/sap/sapgenpse"},
        ),
        (
            {"user": "saprouter", "path": "/usr/sap/sapgenpse", "interval": 30},
            {"deployment": ("sync", None), "user": "saprouter", "path": "/usr/sap/sapgenpse"},
        ),
        (
            {"user": "saprouter", "path": "/usr/sap/sapgenpse", "interval": 86400},
            {
                "deployment": ("cached", 86400.0),
                "user": "saprouter",
                "path": "/usr/sap/sapgenpse",
            },
        ),
    ],
)
def test_migrate(old_value: object, expected: object) -> None:
    assert migrate(old_value) == expected


def test_migrate_already_migrated() -> None:
    already = {"deployment": ("sync", None), "user": "admin", "path": "/opt/sapgenpse"}
    assert migrate(already) == already


def test_migrate_invalid() -> None:
    with pytest.raises(ValueError):
        migrate("unexpected")
