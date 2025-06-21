#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site

from cmk.utils.urls import is_allowed_url

from cmk.gui.config import active_config
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


def page_index() -> None:
    # Redirect to mobile GUI if we are a mobile device and the index is requested
    if is_mobile(request, response):
        raise HTTPRedirect(makeuri(request, [], filename="mobile.py"))

    title = get_page_heading()
    content = HTMLWriter.render_iframe("", src=_get_start_url(), name="main")
    SidebarRenderer().show(title, content)


def _get_start_url() -> str:
    default_start_url = user.start_url or active_config.start_url
    if not is_allowed_url(default_start_url):
        default_start_url = "dashboard.py"

    return request.get_url_input("start_url", default_start_url)


def get_page_heading() -> str:
    if "%s" in active_config.page_heading:
        return active_config.page_heading % (active_config.sites[omd_site()]["alias"])
    return active_config.page_heading
