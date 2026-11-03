#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageEndpoint, PageRegistry

from ._notification_images import AjaxGraphImagesForNotifications


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("ajax_graph_images", AjaxGraphImagesForNotifications()))
