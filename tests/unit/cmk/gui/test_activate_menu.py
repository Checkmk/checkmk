#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.activate_menu import register
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.main_menu_types import ConfigurableMainMenuItem
from cmk.gui.userdb.store import save_custom_attr
from cmk.shared_typing.main_menu import NavItemIdEnum


def _changes_item() -> ConfigurableMainMenuItem:
    registry = MainMenuRegistry()
    register(registry)
    item = registry[NavItemIdEnum.changes]
    if not isinstance(item, ConfigurableMainMenuItem):
        raise TypeError(f"unexpected Changes item: {item!r}")
    return item


def test_full_page_changes_link_is_hidden_from_a_user_who_may_not_activate(
    monkeypatch: pytest.MonkeyPatch, with_user_login: UserId
) -> None:
    save_custom_attr(with_user_login, "navbar_changes_action", "full_page")
    item = _changes_item()

    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda permission: False)  # noqa: ARG005
        nav_item = item.get_item_instance(item, user)
        hidden = nav_item.hide is not None and nav_item.hide()

    assert hidden
