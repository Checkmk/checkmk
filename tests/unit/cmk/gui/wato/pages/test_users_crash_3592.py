#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.type_defs import UserSpec
from cmk.gui.wato.pages.users import ModeUsers


@pytest.mark.usefixtures("request_context", "patch_theme", "with_admin_login")
def test_show_user_list_without_locked_field(test_edition: Edition) -> None:
    mode = ModeUsers(test_edition, PageContext(config=Config(), request=request))
    users = {
        UserId("u1"): UserSpec(alias="User one"),
    }

    mode._show_user_list(
        users, custom_user_attributes=[], user_online_maxage=2592000, table_row_limit=100
    )
