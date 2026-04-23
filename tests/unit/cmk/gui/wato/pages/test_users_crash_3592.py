#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui.type_defs import UserSpec
from cmk.gui.wato.pages.users import ModeUsers


@pytest.mark.xfail(
    strict=True,
    reason="Crash group 3592: KeyError 'locked' on sparse UserSpec",
)
@pytest.mark.usefixtures("request_context", "patch_theme")
def test_show_user_list_without_locked_field(test_edition: Edition) -> None:
    mode = ModeUsers(test_edition)
    users = {
        UserId("u1"): UserSpec(alias="User one"),
    }

    mode._show_user_list(users, custom_user_attributes=[], user_online_maxage=2592000)
