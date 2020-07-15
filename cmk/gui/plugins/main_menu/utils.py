#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu - Shared main module and plugin code

Place for shared code between the main module (cmk.gui.main_menu) and the plugins
in cmk.gui.plugins.main_menu.
"""

from typing import NamedTuple, List, Callable, Optional

from cmk.utils.plugin_registry import InstanceRegistry

TopicMenuItem = NamedTuple("TopicMenuItem", [
    ("name", str),
    ("title", str),
    ("url", str),
    ("sort_index", int),
    ("is_advanced", bool),
    ("icon_name", Optional[str]),
])

TopicMenuTopic = NamedTuple("TopicMenuTopic", [
    ("name", "str"),
    ("title", "str"),
    ("items", List[TopicMenuItem]),
    ("icon_name", Optional[str]),
])

MegaMenu = NamedTuple("MegaMenu", [
    ("name", str),
    ("title", str),
    ("icon_name", str),
    ("sort_index", int),
    ("topics", Callable[[], List[TopicMenuTopic]]),
])


class MegaMenuRegistry(InstanceRegistry):
    def plugin_base_class(self):
        return MegaMenu


mega_menu_registry = MegaMenuRegistry()
