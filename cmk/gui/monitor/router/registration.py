#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.monitor.setup_folders import SetupFolderSource
from cmk.gui.pages import PageEndpoint, PageRegistry

from ._page import MonitorRouterPage


def register(page_registry: PageRegistry, setup_folders: SetupFolderSource) -> None:
    page_registry.register(PageEndpoint("monitor_search", MonitorRouterPage(setup_folders)))
