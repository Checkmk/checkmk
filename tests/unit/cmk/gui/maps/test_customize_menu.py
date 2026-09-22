#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Maps is offered in the Customize menu, and the entry leads somewhere.

The menu builder links every declared pagetype to ``<type_name>s.py`` without
checking that such a page exists, so a declared type whose page is missing puts a
dead link into the menu -- which is what the GUI crawl trips over.
"""

from cmk.gui import pagetypes
from cmk.gui.pages import page_registry


def test_map_is_offered_in_the_customize_menu(load_plugins: None) -> None:  # noqa: ARG001
    assert "map" in pagetypes.all_page_types()


def test_the_customize_entry_leads_to_a_registered_page(load_plugins: None) -> None:  # noqa: ARG001
    menu_url = f"{pagetypes.page_type('map').type_name()}s.py"

    assert page_registry.get(menu_url.removesuffix(".py")) is not None
