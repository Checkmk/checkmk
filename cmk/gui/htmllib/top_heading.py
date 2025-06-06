#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from cmk.utils.licensing.registry import get_licensing_user_effect

from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbRenderer
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.http import Request
from cmk.gui.http import request as _request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import PageMenu, PageMenuPopupsRenderer, PageMenuRenderer
from cmk.gui.page_state import PageState
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri_contextless

from .debug_vars import debug_vars
from .generator import HTMLWriter


def top_heading(
    writer: HTMLWriter,
    request: Request,
    title: str,
    breadcrumb: Breadcrumb,
    page_menu: PageMenu | None = None,
    *,
    browser_reload: float,
    debug: bool,
) -> None:
    _may_show_license_expiry(writer)

    writer.open_div(id_="top_heading")
    writer.open_div(class_="titlebar")
    writer.open_div()

    # We don't want to handle "title" permissive.
    html_title = HTML.with_escaping(title)
    writer.a(
        html_title,
        class_="title",
        href="#",
        onfocus="if (this.blur) this.blur();",
        onclick="this.innerHTML='%s'; document.location.reload();" % _("Reloading..."),
    )

    if breadcrumb:
        BreadcrumbRenderer().show(breadcrumb)

    writer.close_div()

    _may_show_license_banner(writer)

    writer.close_div()  # titlebar

    if page_menu:
        PageMenuRenderer().show(
            page_menu,
            hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        )

    writer.close_div()  # top_heading

    if page_menu:
        PageMenuPopupsRenderer().show(page_menu)

    if debug:
        _dump_get_vars(
            writer,
            request,
        )


def _may_show_license_expiry(writer: HTMLWriter) -> None:
    if (
        header_effect := get_licensing_user_effect(
            licensing_settings_link=makeuri_contextless(
                _request, [("mode", "licensing")], filename="wato.py"
            )
        ).header
    ) and (set(header_effect.roles).intersection(user.role_ids)):
        writer.show_warning(HTML.without_escaping(header_effect.message_html))


def _may_show_license_banner(writer: HTMLWriter) -> None:
    if (
        header_effect := get_licensing_user_effect(
            licensing_settings_link=makeuri_contextless(
                _request, [("mode", "licensing")], filename="wato.py"
            )
        ).banner
    ) and (set(header_effect.roles).intersection(user.role_ids)):
        writer.write_html(HTML.without_escaping(header_effect.message_html))


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
