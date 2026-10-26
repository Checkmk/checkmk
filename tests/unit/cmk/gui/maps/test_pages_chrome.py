#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.maps.gui._pages import _list_layout
from cmk.maps.gui._settings import map_object_defaults


def _ctx() -> PageContext:
    return PageContext(
        config=Config(),
        request=request,
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(Config(), all_permissions()),
    )


def test_list_layout_is_the_global_default_until_one_is_chosen(
    request_context: None, with_admin_login: UserId
) -> None:
    assert _list_layout(_ctx()) == map_object_defaults()["map_list_view"]


def test_list_layout_is_the_one_requested(request_context: None, with_admin_login: UserId) -> None:
    request.set_var("layout", "table")
    assert _list_layout(_ctx()) == "table"


def test_list_layout_chosen_once_is_kept_on_the_way_back(
    request_context: None, with_admin_login: UserId
) -> None:
    request.set_var("layout", "table")
    _list_layout(_ctx())
    request.del_var("layout")
    assert _list_layout(_ctx()) == "table"


def test_unknown_list_layout_is_ignored(request_context: None, with_admin_login: UserId) -> None:
    request.set_var("layout", "<script>")
    assert _list_layout(_ctx()) == map_object_defaults()["map_list_view"]
