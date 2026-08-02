#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Composer for self-rendering ``cmk.web`` feature pages."""

from collections.abc import Sequence

from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_main_menu_breadcrumb,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import PageContext, PageEndpoint
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.utils.transaction_manager import TransactionManager, transactions
from cmk.gui.utils.urls import makeactionuri
from cmk.web.context import ActionUrlBuilder
from cmk.web.exceptions import MKUserError as WebMKUserError
from cmk.web.page_container import PageContainer, PageContainerMenu
from cmk.web.pages import Page as WebPage
from cmk.web.pages import PageContext as WebPageContext
from cmk.web.utils.html import HTML


def web_page_endpoint(ident: str, page: WebPage) -> PageEndpoint:
    """Wrap a ``cmk.web`` feature page into a registry endpoint."""

    def handler(ctx: PageContext) -> None:
        _render(page, ctx)

    return PageEndpoint(ident, handler)


def _make_action_url_builder(
    request: Request, transactions: TransactionManager
) -> ActionUrlBuilder:
    def make_action_url(variables: Sequence[tuple[str, str | int | None]], *, filename: str) -> str:
        return makeactionuri(request, transactions.get(), list(variables), filename=filename)

    return make_action_url


def _render(page: WebPage, gui_ctx: PageContext) -> None:
    web_ctx = WebPageContext(
        request=gui_ctx.request,
        user=user,
        i18n=_,
        make_action_url=_make_action_url_builder(gui_ctx.request, transactions),
    )
    try:
        container = page.page(web_ctx)
    except WebMKUserError as exc:
        raise MKUserError(exc.varname, exc.message) from exc

    breadcrumb = _to_breadcrumb(container)
    make_header(
        html,
        title=container.title,
        breadcrumb=breadcrumb,
        page_menu=_to_page_menu(container.page_menu, breadcrumb),
        debug=gui_ctx.config.debug,
        lang=user.language,
        inject_js_profiling_code=gui_ctx.config.inject_js_profiling_code,
        load_frontend_vue=gui_ctx.config.load_frontend_vue,
        custom_style_sheet=gui_ctx.config.custom_style_sheet,
        screenshotmode=gui_ctx.config.screenshotmode,
        inline_help_as_text=user.inline_help_as_text,
        hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        user_role_ids=user.role_ids,
    )
    html.write_html(HTML.without_escaping(container.content))
    html.footer()


def _to_breadcrumb(container: PageContainer) -> Breadcrumb:
    breadcrumb = make_main_menu_breadcrumb(main_menu_registry.menu_help())
    if not container.breadcrumb:
        return breadcrumb
    *intermediate, current = container.breadcrumb
    for item in intermediate:
        breadcrumb.append(BreadcrumbItem(title=item.title, url=item.url, id=None))
    breadcrumb.append(make_current_page_breadcrumb_item(current.title))
    return breadcrumb


def _to_page_menu(menu: PageContainerMenu | None, breadcrumb: Breadcrumb) -> PageMenu | None:
    if menu is None:
        return None
    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name=dropdown.name,
                title=dropdown.title,
                topics=[
                    PageMenuTopic(
                        title=topic.title,
                        entries=[
                            PageMenuEntry(
                                title=entry.title,
                                icon_name=StaticIcon(IconNames(entry.icon_name)),
                                item=make_simple_link(entry.url),
                                is_enabled=entry.is_enabled,
                                is_shortcut=entry.is_shortcut,
                                is_suggested=entry.is_suggested,
                            )
                            for entry in topic.entries
                        ],
                    )
                    for topic in dropdown.topics
                ],
            )
            for dropdown in menu.dropdowns
        ],
        breadcrumb=breadcrumb,
    )
