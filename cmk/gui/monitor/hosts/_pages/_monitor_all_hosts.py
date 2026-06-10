#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
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
from cmk.gui.pages import PageContext
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.permissions import permission_registry
from cmk.gui.top_heading import top_heading
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless
from cmk.shared_typing.monitoring.all_hosts import MonitoringAllHostsApp

_PAGE_TITLE = _("All hosts (experimental)")


def page_monitor_all_hosts(ctx: PageContext) -> None:
    breadcrumb = _make_breadcrumb(ctx)

    html.body_start(
        str(_PAGE_TITLE),
        lang=user.language,
        inject_js_profiling_code=ctx.config.inject_js_profiling_code,
        load_frontend_vue=ctx.config.load_frontend_vue,
        custom_style_sheet=ctx.config.custom_style_sheet,
        screenshotmode=ctx.config.screenshotmode,
        inline_help_as_text=user.inline_help_as_text,
    )

    top_heading(
        html,
        request,
        str(_PAGE_TITLE),
        breadcrumb,
        page_menu=_build_page_menu(breadcrumb),
        # Vue app will handle its own polling — no browser-level reload timer.
        browser_reload=0.0,
        debug=ctx.config.debug,
        hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        user_role_ids=user.role_ids,
    )

    html.begin_page_content(enable_scrollbar=False)
    html.vue_component(
        "cmk-monitoring-all-hosts",
        data=asdict(
            MonitoringAllHostsApp(
                poll_interval_ms=ctx.config.view_option_refreshes[0] * 1000,
            )
        ),
    )
    html.end_page_content()

    html.body_end()


def _make_breadcrumb(ctx: PageContext) -> Breadcrumb:
    user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
    breadcrumb = make_topic_breadcrumb(
        main_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic("overview", user_permissions).title(),
    )
    breadcrumb.append(
        BreadcrumbItem(
            title=_PAGE_TITLE,
            url=makeuri_contextless(request, [], filename="monitor_all_hosts.py"),
            id="monitor_all_hosts",
        )
    )
    return breadcrumb


def _build_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    availability_url = makeuri_contextless(
        request,
        [("view_name", "allhosts"), ("mode", "availability")],
        filename="view.py",
    )

    menu = PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="availability",
                title=_("Availability"),
                topics=[
                    PageMenuTopic(
                        title=_("This view"),
                        entries=[
                            PageMenuEntry(
                                title=_("Availability"),
                                icon_name=StaticIcon(IconNames.availability),
                                item=make_simple_link(availability_url),
                                name="availability",
                                is_shortcut=False,
                                is_suggested=False,
                            )
                        ],
                    )
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )

    # PageMenu.__post_init__ appends "display" and "help" dropdowns automatically.
    # We remove "display" entirely, because the Vue app will own its display controls.
    # We keep "help" but strip the "inline_help" entry since this page has no
    # inline help content.
    menu.dropdowns = [d for d in menu.dropdowns if d.name != "display"]
    help_dropdown = menu["help"]
    for topic in help_dropdown.topics:
        topic.entries = [e for e in topic.entries if e.name != "inline_help"]

    return menu
