#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.welcome.pages as welcome_pages
import cmk.gui.welcome.snapin as welcome_snapin
from cmk.gui.pages import PageRegistry
from cmk.gui.sidebar import SnapinRegistry


def register(page_registry: PageRegistry, snapin_registry: SnapinRegistry) -> None:
    welcome_pages.register(page_registry)
    welcome_snapin.register(snapin_registry)
