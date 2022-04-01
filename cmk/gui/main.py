#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.site import omd_site

import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.globals import config, html, request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.sidebar import SidebarRenderer
from cmk.gui.sites import get_site_config
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri


@cmk.gui.pages.register("index")
def page_index() -> None:
    # Redirect to mobile GUI if we are a mobile device and the index is requested
    if is_mobile(request, response):
        raise HTTPRedirect(makeuri(request, [], filename="mobile.py"))

    title = get_page_heading()
    content = html.render_iframe("", src=_get_start_url(), name="main")
    SidebarRenderer().show(title, content)


def _get_start_url() -> str:
    default_start_url = user.start_url or config.start_url
    if not utils.is_allowed_url(default_start_url):
        default_start_url = "dashboard.py"

    return request.get_url_input("start_url", default_start_url)


def get_page_heading() -> str:
    if "%s" in config.page_heading:
        return config.page_heading % (get_site_config(omd_site()).get("alias", _("GUI")))
    return config.page_heading
