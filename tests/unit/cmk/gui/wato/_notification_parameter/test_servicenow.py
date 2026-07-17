#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.wato._notification_parameter._servicenow import _migrate_auth_section


@pytest.mark.parametrize(
    "old_password",
    [
        pytest.param(("store", "password_1"), id="Password from password store"),
        pytest.param(("password", "mypassword"), id="Explicit password"),
    ],
)
def test_migrate_auth_section_preserves_password(
    old_password: tuple[str, str],
) -> None:
    migrated = _migrate_auth_section({"username": "username", "password": old_password})
    assert migrated["auth"] == (
        "auth_basic",
        {"username": "username", "password": old_password},
    )


def test_migrate_auth_section_leaves_already_migrated_untouched() -> None:
    params = {"auth": ("auth_basic", {"username": "username", "password": ("store", "password_1")})}
    assert _migrate_auth_section(params) is params
