#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.plugin_loader import load_plugins

#.
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'

from cmk.gui.plugins.sidebar.utils import (  # noqa: F401 # pylint: disable=unused-import
    SidebarSnapin, PageHandlers, CustomizableSidebarSnapin, snapin_registry, snapin_width,
    snapin_site_choice, visuals_by_topic, render_link, heading, link, simplelink, bulletlink,
    iconlink, nagioscgilink, footnotelinks, begin_footnote_links, end_footnote_links,
    write_snapin_exception,
)

#.
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'

load_plugins(__file__, __package__)
