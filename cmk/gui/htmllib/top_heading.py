#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from datetime import datetime

from cmk.utils.licensing.state import is_licensed
from cmk.utils.version import is_raw_edition

import cmk.gui.utils.escaping as escaping
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbRenderer
from cmk.gui.config import active_config
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import PageMenu, PageMenuPopupsRenderer, PageMenuRenderer
from cmk.gui.page_state import PageState, PageStateRenderer
from cmk.gui.utils.html import HTML

from .debug_vars import debug_vars
from .generator import HTMLWriter

if not is_raw_edition():  # TODO solve this via registration
    from cmk.utils.cee.licensing import (  # type: ignore[import]  # pylint: disable=no-name-in-module, import-error
        get_days_until_expiration,
        in_admin_warning_header_phase,
        in_user_warning_header_phase,
        load_verification_response,
    )


def top_heading(
    writer: HTMLWriter,
    request: Request,
    title: str,
    breadcrumb: Breadcrumb,
    page_menu: PageMenu | None = None,
    page_state: PageState | None = None,
    *,
    browser_reload: float,
) -> None:
    _may_show_license_expiry(writer)

    writer.open_div(id_="top_heading")
    writer.open_div(class_="titlebar")

    # HTML() is needed here to prevent a double escape when we do  self._escape_attribute
    # here and self.a() escapes the content (with permissive escaping) again. We don't want
    # to handle "title" permissive.
    html_title = HTML(escaping.escape_attribute(title))
    writer.a(
        html_title,
        class_="title",
        href="#",
        onfocus="if (this.blur) this.blur();",
        onclick="this.innerHTML='%s'; document.location.reload();" % _("Reloading..."),
    )

    if breadcrumb:
        BreadcrumbRenderer().show(breadcrumb)

    if page_state is None:
        page_state = _make_default_page_state(
            writer,
            request,
            browser_reload=browser_reload,
        )

    if page_state:
        PageStateRenderer().show(page_state)

    writer.close_div()  # titlebar

    if page_menu:
        PageMenuRenderer().show(
            page_menu,
            hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        )

    writer.close_div()  # top_heading

    if page_menu:
        PageMenuPopupsRenderer().show(page_menu)

    if active_config.debug:
        _dump_get_vars(
            writer,
            request,
        )


def _may_show_license_expiry(writer: HTMLWriter) -> None:
    if is_raw_edition():  # TODO: cleanup conditional imports and solve this via registration
        return
    now = int(datetime.now().timestamp())
    if not is_licensed():
        return
    if (response := load_verification_response()) is None:
        return

    if in_user_warning_header_phase(now, response):
        # TODO change to correct link once available
        licensing_link = "https://checkmk.com/contact"
        writer.show_warning(
            _("Your license is expired since %s. See here how to proceed: %s")
            % (
                datetime.fromtimestamp(response.subscription_expiration_ts).strftime("%Y-%m-%d"),
                licensing_link,
            )
        )
        return

    if "admin" in user.role_ids and in_admin_warning_header_phase(now, response):
        writer.show_warning(
            _("Your license expires in %i days")
            % get_days_until_expiration(now, response.subscription_expiration_ts)
        )


def _make_default_page_state(
    writer: HTMLWriter, request: Request, *, browser_reload: float
) -> PageState | None:
    """Create a general page state for all pages without specific one"""
    if not browser_reload:
        return None

    return PageState(
        text=writer.render_span("%d" % browser_reload),
        icon_name="trans",
        css_classes=["reload"],
        url="javascript:document.location.reload()",
        tooltip_text=_("Automatic page reload in %d seconds.") % browser_reload
        + "\n"
        + _("Click for instant reload."),
    )


def _dump_get_vars(
    writer: HTMLWriter,
    request: Request,
) -> None:
    with foldable_container(
        treename="html",
        id_="debug_vars",
        isopen=True,
        title=_("GET/POST variables of this page"),
    ):
        debug_vars(writer, request, hide_with_mouse=False)
