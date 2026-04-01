#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence

from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbRenderer
from cmk.gui.htmllib.debug_vars import debug_vars
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import Request
from cmk.gui.http import request as _request
from cmk.gui.i18n import _
from cmk.gui.page_menu import PageMenu, PageMenuPopupsRenderer, PageMenuRenderer
from cmk.gui.page_state import PageState, PageStateRenderer
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri_contextless
from cmk.licensing.registry import get_licensing_user_effect
from cmk.utils import paths


def top_heading(
    writer: HTMLWriter,
    request: Request,
    title: str,
    breadcrumb: Breadcrumb,
    page_menu: PageMenu | None = None,
    *,
    browser_reload: float,
    debug: bool,
    hide_suggestions: bool,
    user_role_ids: Sequence[str],
) -> None:
    _may_show_license_expiry(writer, user_role_ids)

    writer.open_div(id_="top_heading")
    writer.open_div(class_="titlebar")
    writer.open_div()

    if breadcrumb:
        BreadcrumbRenderer().show(breadcrumb)

    # We don't want to handle "title" permissive.
    html_title = HTML.with_escaping(title)
    writer.a(
        html_title,
        title=title,
        class_="title",
        href="#",
        onfocus="if (this.blur) this.blur();",
        onclick="this.innerHTML='%s'; document.location.reload();" % _("Reloading..."),
    )

    writer.close_div()

    page_state = _make_default_page_state(
        writer,
        request,
        browser_reload=browser_reload,
    )

    _may_show_license_banner(writer, user_role_ids)

    if page_state:
        PageStateRenderer().show(page_state)

    writer.close_div()  # titlebar

    if page_menu:
        PageMenuRenderer().show(
            page_menu,
            hide_suggestions=hide_suggestions,
        )

    writer.close_div()  # top_heading

    if page_menu:
        PageMenuPopupsRenderer().show(page_menu)

    if debug:
        _dump_get_vars(
            writer,
            request,
        )


def _may_show_license_expiry(writer: HTMLWriter, user_role_ids: Sequence[str]) -> None:
    if (
        header_effect := get_licensing_user_effect(
            paths.omd_root,
            licensing_settings_link=makeuri_contextless(
                _request, [("mode", "licensing")], filename="wato.py"
            ),
        ).header
    ) and (set(header_effect.roles).intersection(user_role_ids)):
        writer.show_warning(HTML.without_escaping(header_effect.message_html))


def _may_show_license_banner(writer: HTMLWriter, user_role_ids: Sequence[str]) -> None:
    if (
        header_effect := get_licensing_user_effect(
            paths.omd_root,
            licensing_settings_link=makeuri_contextless(
                _request, [("mode", "licensing")], filename="wato.py"
            ),
        ).banner
    ) and (set(header_effect.roles).intersection(user_role_ids)):
        writer.write_html(HTML.without_escaping(header_effect.message_html))


def _make_default_page_state(
    writer: HTMLWriter, request: Request, *, browser_reload: float
) -> PageState | None:
    """Create a general page state for all pages without specific one"""
    if not browser_reload:
        return None

    return PageState(
        text=writer.render_span("%d" % browser_reload),
        icon_name=StaticIcon(IconNames.trans),
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
