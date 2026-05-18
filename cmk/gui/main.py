#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site
from cmk.gui.config import Config, get_page_heading
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import Request, response
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.permissions import permission_registry
from cmk.gui.sidebar import SidebarRenderer
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import add_kiosk_to_url, is_kiosk_request, makeuri
from cmk.utils.urls import is_allowed_url


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("index", page_index))


def page_index(ctx: PageContext) -> None:
    # Redirect to mobile GUI if we are a mobile device and the index is requested
    if is_mobile(ctx.request, response):
        raise HTTPRedirect(makeuri(ctx.request, [], filename="mobile.py"))

    kiosk = is_kiosk_request(ctx.request)
    SidebarRenderer().show(
        config=ctx.config,
        user_permissions=UserPermissions.from_config(ctx.config, permission_registry),
        title=get_page_heading(ctx.config, omd_site()),
        content=HTMLWriter.render_iframe(
            "", src=_get_start_url(ctx.request, ctx.config, kiosk=kiosk), name="main"
        ),
        sidebar_config=ctx.config.sidebar,
        screenshot_mode=ctx.config.screenshotmode,
        sidebar_notify_interval=ctx.config.sidebar_notify_interval,
        start_url=ctx.config.start_url,
        show_scrollbar=ctx.config.sidebar_show_scrollbar,
        sidebar_update_interval=ctx.config.sidebar_update_interval,
        kiosk=kiosk,
    )


def _get_start_url(request: Request, config: Config, *, kiosk: bool = False) -> str:
    default_start_url = user.start_url or config.start_url
    if not is_allowed_url(default_start_url):
        default_start_url = "dashboard.py"

    start_url = request.get_url_input("start_url", default_start_url)
    return add_kiosk_to_url(start_url) if kiosk else start_url
