#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.utils as utils
from cmk.gui.globals import html, request
from cmk.gui.sidebar import SidebarRenderer
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.utils.urls import makeuri


@cmk.gui.pages.register("index")
def page_index() -> None:
    # Redirect to mobile GUI if we are a mobile device and the index is requested
    if html.is_mobile():
        raise HTTPRedirect(makeuri(request, [], filename="mobile.py"))

    title = config.get_page_heading()
    content = html.render_iframe("", src=_get_start_url(), name="main")
    SidebarRenderer().show(title, content)


def _get_start_url() -> str:
    default_start_url = config.user.get_attribute("start_url", config.start_url) or config.start_url
    if not utils.is_allowed_url(default_start_url):
        default_start_url = "dashboard.py"

    return html.get_url_input("start_url", default_start_url)
