#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.views.command.registry import CommandRegistry

from ._monitor_all_hosts import MonitorAllHostsPage


def register_pages(
    page_registry: PageRegistry,
    command_registry: CommandRegistry,
) -> None:
    page_registry.register(PageEndpoint("monitor_all_hosts", MonitorAllHostsPage(command_registry)))
