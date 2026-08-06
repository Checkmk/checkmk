#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.monitor.command import MonitorCommands
from cmk.gui.pages import PageEndpoint, PageRegistry

from ._monitor_host_services import MonitorHostServicesPage


def register_pages(page_registry: PageRegistry, command_registry: MonitorCommands) -> None:
    page_registry.register(
        PageEndpoint("monitor_host_services", MonitorHostServicesPage(command_registry))
    )
