#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.pages import PageEndpoint, PageRegistry

from ._monitor_all_hosts import page_monitor_all_hosts


def register_pages(
    page_registry: PageRegistry,
) -> None:
    page_registry.register(PageEndpoint("monitor_all_hosts", page_monitor_all_hosts))
