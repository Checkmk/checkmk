#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from cmk.gui.exceptions import MKAuthException
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato.pages.user_profile import change_password as change_password_mod
from cmk.gui.wato.pages.user_profile.change_password import UserChangePasswordPage
from cmk.gui.wato.pages.user_profile.main_menu import default_user_menu_topics


@pytest.fixture(name="stub_user_menu_quick_entries")
def fixture_stub_user_menu_quick_entries() -> Iterator[None]:
    # The "Color theme" and "Sidebar position" quick entries need a populated
    # theme registry and a user attribute on disk — neither exists in the
    # unit-test web_dir. Stub them so the menu renders.
    base = "cmk.gui.wato.pages.user_profile.main_menu"
    with (
        patch(f"{base}._get_current_theme_title", return_value="Default"),
        patch(f"{base}._get_sidebar_position", return_value="right"),
    ):
        yield


@pytest.mark.usefixtures("with_admin_login", "remote_site", "stub_user_menu_quick_entries")
def test_main_menu_omits_change_password_on_remote_site() -> None:
    topics = default_user_menu_topics(UserPermissions({}, {}, {}, []))
    user_profile_topic = next(t for t in topics if t.id == "user_profile")
    assert "change_password" not in [e.id for e in user_profile_topic.entries]


def test_change_password_action_blocked_on_remote_site(monkeypatch: pytest.MonkeyPatch) -> None:
    """The change-password action raises ``MKAuthException`` on a remote site before reading or writing any password."""
    monkeypatch.setattr(
        change_password_mod, "is_distributed_setup_remote_site", lambda _sites: True
    )
    page = UserChangePasswordPage(MagicMock())  # edition is irrelevant to the guard
    with pytest.raises(MKAuthException, match="remote sites"):
        page._action(request=MagicMock(), config=MagicMock())  # noqa: SLF001
