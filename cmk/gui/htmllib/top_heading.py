#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from cmk.utils.licensing.state import is_licensed, is_trial
from cmk.utils.version import is_cloud_edition, is_raw_edition

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
    from cmk.utils.cee.licensing.helper import (  # type: ignore[import]  # pylint: disable=no-name-in-module, import-error
        get_num_services_for_trial_free_edition,
    )
    from cmk.utils.cee.licensing.state import (  # type: ignore[import]  # pylint: disable=no-name-in-module, import-error
        load_verified_response,
    )
    from cmk.utils.cee.licensing.user_effects import (  # type: ignore[import]  # pylint: disable=no-name-in-module, import-error
        licensing_user_effect_licensed,
        licensing_user_effect_trial,
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
    if not is_cloud_edition():  # TODO: cleanup conditional imports and solve this via registration
        return

    if is_trial():
        effect = licensing_user_effect_trial(get_num_services_for_trial_free_edition())
        if effect.header and (set(effect.header.roles).intersection(user.role_ids)):
            writer.show_warning(effect.header.message)
        return

    if is_licensed() and (verified_response := load_verified_response()) is not None:
        effect = licensing_user_effect_licensed(verified_response.response)
        if effect.header and (set(effect.header.roles).intersection(user.role_ids)):
            writer.show_warning(effect.header.message)


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
