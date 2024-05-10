#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.http import request
from cmk.gui.wato.pages.users import ModeEditUser, ModeUsers


def test_users_breadcrumb_dont_list_users_topic(request_context: None) -> None:
    assert list(ModeUsers().breadcrumb()) == [
        BreadcrumbItem(title="Users", url="wato.py?mode=users"),
    ]


def test_edituser_breadcrumb_dont_list_users_topic(request_context: None) -> None:
    request.set_var("user", "testuser")
    assert list(ModeEditUser().breadcrumb()) == [
        BreadcrumbItem(title="Users", url="wato.py?mode=users"),
        BreadcrumbItem(title="Edit user testuser", url="wato.py?edit=testuser&mode=edit_user"),
    ]
