#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.gui.main_menu import MegaMenuRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.type_defs import TopicMenuTopic

from . import async_replication, change_password, edit_profile, mega_menu, replicate, two_factor


def register(
    page_registry: PageRegistry,
    mega_menu_registry: MegaMenuRegistry,
    user_menu_topics: Callable[[], list[TopicMenuTopic]],
) -> None:
    mega_menu.register(page_registry, mega_menu_registry, user_menu_topics)
    two_factor.register(page_registry)
    two_factor.register(page_registry)
    edit_profile.register(page_registry)
    change_password.register(page_registry)
    async_replication.register(page_registry)
    replicate.register(page_registry)
