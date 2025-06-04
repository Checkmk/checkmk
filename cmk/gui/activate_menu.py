#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui import site_config
from cmk.gui.config import active_config
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.type_defs import (
    MainMenu,
    MainMenuItem,
    MainMenuTopic,
)


def _hide_menu() -> bool:
    if not user.may("wato.activate"):
        return True
    return site_config.is_wato_slave_site() and not active_config.wato_enabled


def register(mega_menu_registry: MainMenuRegistry) -> None:
    mega_menu_registry.register(
        MainMenu(
            name="changes",
            title=_l("Changes"),
            icon="main_changes",
            sort_index=17,
            topics=lambda: [
                MainMenuTopic(
                    name="changes",
                    title=_("Activate changes"),
                    icon="main_changes",
                    entries=[
                        MainMenuItem(
                            name="changes",
                            title=_("Activate changes"),
                            sort_index=11,
                            icon="main_changes",
                            url="wato.py?mode=changelog",
                        ),
                    ],
                )
            ],
            hide=_hide_menu,
        )
    )
