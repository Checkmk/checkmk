#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from unittest.mock import patch

import pytest


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
