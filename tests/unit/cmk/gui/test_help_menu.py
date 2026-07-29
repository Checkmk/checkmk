#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import help_menu
from cmk.gui.main_menu import MainMenuRegistry


def test_unack_incomp_werks_button_links_to_filtered_werks(request_context: None) -> None:
    registry = MainMenuRegistry()
    help_menu.register(
        registry,
        help_menu.default_info_line,
        list,
        list,
        list,
    )

    header = registry.menu_help().header
    assert header is not None
    assert header.trigger_button is not None
    assert header.trigger_button.target_url == "change_log.py?show_unack=1"
