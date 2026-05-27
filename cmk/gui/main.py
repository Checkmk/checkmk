#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.http import Request, response
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import add_kiosk_to_url, is_kiosk_request, makeuri
from cmk.utils.urls import is_allowed_url


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("index", page_index))


def page_index(ctx: PageContext) -> None:
    """Resolve the user's start page and redirect to it.

    The historical role of ``index.py`` was to render a top-level frameset
    that hosted the sidebar plus an iframe loading the actual content page.
    The iframe has been removed; content pages now render their own
    navigation and sidebar via :func:`cmk.gui.header.make_header`.
    ``index.py`` exists only to keep old bookmarks of the form
    ``index.py?start_url=X`` working and to land users on their configured
    start page when they request the site root.
    """
    if is_mobile(ctx.request, response):
        raise HTTPRedirect(makeuri(ctx.request, [], filename="mobile.py"))
    kiosk = is_kiosk_request(ctx.request)
    raise HTTPRedirect(_get_start_url(ctx.request, ctx.config, kiosk=kiosk))


def _get_start_url(request: Request, config: Config, *, kiosk: bool = False) -> str:
    default_start_url = user.start_url or config.start_url
    if not is_allowed_url(default_start_url):
        default_start_url = "dashboard.py"

    start_url = request.get_url_input("start_url", default_start_url)
    return add_kiosk_to_url(start_url) if kiosk else start_url
