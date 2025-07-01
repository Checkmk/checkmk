#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site

from cmk.utils.urls import is_allowed_url

from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.sidebar import SidebarRenderer
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("index", page_index))


def page_index(config: Config) -> None:
    # Redirect to mobile GUI if we are a mobile device and the index is requested
    if is_mobile(request, response):
        raise HTTPRedirect(makeuri(request, [], filename="mobile.py"))

    SidebarRenderer().show(
        config=config,
        title=get_page_heading(config),
        content=HTMLWriter.render_iframe("", src=_get_start_url(config), name="main"),
        sidebar_config=config.sidebar,
        screenshot_mode=config.screenshotmode,
        sidebar_notify_interval=config.sidebar_notify_interval,
        start_url=config.start_url,
        show_scrollbar=config.sidebar_show_scrollbar,
        sidebar_update_interval=config.sidebar_update_interval,
    )


def _get_start_url(config: Config) -> str:
    default_start_url = user.start_url or config.start_url
    if not is_allowed_url(default_start_url):
        default_start_url = "dashboard.py"

    return request.get_url_input("start_url", default_start_url)


def get_page_heading(config: Config) -> str:
    if "%s" in config.page_heading:
        return config.page_heading % (config.sites[omd_site()]["alias"])
    return config.page_heading
