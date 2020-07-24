#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu - Shared main module and plugin code

Place for shared code between the main module (cmk.gui.main_menu) and the plugins
in cmk.gui.plugins.main_menu.
"""

from typing import List

from cmk.gui.type_defs import (
    MegaMenu,
    TopicMenuTopic,
)
from cmk.utils.plugin_registry import InstanceRegistry


def any_advanced_items(topics: List[TopicMenuTopic]) -> bool:
    return any(item.is_advanced for topic in topics for item in topic.items)


class MegaMenuRegistry(InstanceRegistry):
    def plugin_base_class(self):
        return MegaMenu


mega_menu_registry = MegaMenuRegistry()
