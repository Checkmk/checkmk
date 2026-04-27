#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

import cmk.utils.paths
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import Request
from cmk.gui.pages import PageContext
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato.pages.user_profile.change_password import UserChangePasswordPage
from cmk.gui.wato.pages.user_profile.main_menu import default_user_menu_topics


@pytest.fixture(name="remote_site")
def fixture_remote_site() -> Iterator[None]:
    """Make test believe it's running on a remote site."""
    cmk.utils.paths.check_mk_config_dir.mkdir(parents=True, exist_ok=True)
    distr_wato_mk = cmk.utils.paths.check_mk_config_dir / "distributed_wato.mk"
    previous = distr_wato_mk.read_bytes() if distr_wato_mk.exists() else None
    distr_wato_mk.write_text("is_distributed_setup_remote_site = True\n")
    try:
        yield
    finally:
        if previous is None:
            distr_wato_mk.unlink(missing_ok=True)
        else:
            distr_wato_mk.write_bytes(previous)


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


@pytest.mark.usefixtures("with_admin_login", "remote_site")
def test_change_password_page_blocked_on_remote_site(load_config: Config) -> None:
    page = UserChangePasswordPage(Edition.COMMUNITY)
    ctx = PageContext(config=load_config, request=MagicMock(spec=Request))
    with pytest.raises(MKAuthException):
        page.page(ctx)


@pytest.mark.usefixtures("with_admin_login", "remote_site", "stub_user_menu_quick_entries")
def test_main_menu_omits_change_password_on_remote_site() -> None:
    topics = default_user_menu_topics(UserPermissions({}, {}, {}, []))
    user_profile_topic = next(t for t in topics if t.id == "user_profile")
    assert "change_password" not in [e.id for e in user_profile_topic.entries]
