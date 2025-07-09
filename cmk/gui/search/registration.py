#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageEndpoint, PageRegistry

from .unified import PageUnifiedSearch


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("ajax_unified_search", PageUnifiedSearch))
