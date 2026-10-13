#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Maps is offered in the Customize menu, marked experimental, and the entry leads somewhere.

The menu builder links every declared pagetype to ``<type_name>s.py`` without
checking that such a page exists, so a declared type whose page is missing puts a
dead link into the menu -- which is what the GUI crawl trips over.
"""

import pytest

from cmk.gui import pagetypes
from cmk.gui.config import active_config
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.main_menu_types import MainMenuItem
from cmk.gui.pages import page_registry
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions


@pytest.mark.usefixtures("load_plugins")
def test_map_is_offered_in_the_customize_menu() -> None:
    assert "map" in pagetypes.all_page_types()


@pytest.mark.usefixtures("load_plugins")
def test_the_customize_entry_leads_to_a_registered_page() -> None:
    menu_url = f"{pagetypes.page_type('map').type_name()}s.py"

    assert page_registry.get(menu_url.removesuffix(".py")) is not None


@pytest.mark.usefixtures("load_plugins", "request_context", "with_admin_login")
def test_only_maps_are_marked_experimental_in_the_customize_menu() -> None:
    customize = main_menu_registry["customize"]
    assert isinstance(customize, MainMenuItem) and customize.get_topics is not None
    topics = customize.get_topics(UserPermissions.from_config(active_config, permission_registry))
    titles = {entry.id: entry.title for topic in topics for entry in topic.entries}

    assert titles["map"] == "Maps (experimental)"
    assert titles["bookmark_list"] == "Bookmark lists"
