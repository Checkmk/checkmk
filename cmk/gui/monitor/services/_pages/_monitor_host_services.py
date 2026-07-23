#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import override

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import PageMenu
from cmk.gui.pages import Page, PageContext
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless


class MonitorHostServicesPage(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        hostname = ctx.request.get_validated_type_input_mandatory(HostName, "host")
        # Read for parity with the endpoint's site scoping; not used yet since there is no
        # frontend Vue app to hand it to.
        SiteId(ctx.request.get_str_input_mandatory("site"))
        title = _("Services of host %(host)s") % {"host": hostname}

        breadcrumb = _make_breadcrumb(ctx, title)

        make_header(
            html,
            title=str(title),
            breadcrumb=breadcrumb,
            page_menu=PageMenu(breadcrumb=breadcrumb),
            enable_main_page_scrollbar=False,
            debug=ctx.config.debug,
            lang=user.language,
            inject_js_profiling_code=ctx.config.inject_js_profiling_code,
            load_frontend_vue=ctx.config.load_frontend_vue,
            custom_style_sheet=ctx.config.custom_style_sheet,
            screenshotmode=ctx.config.screenshotmode,
            inline_help_as_text=user.inline_help_as_text,
            hide_suggestions=not user.get_tree_state("suggestions", "all", True),
            user_role_ids=user.role_ids,
        )

        # No Vue app exists yet to mount here; this is a placeholder mount point for it.
        html.vue_component("cmk-monitoring-host-services", data={})

        html.footer()


def _make_breadcrumb(ctx: PageContext, title: str) -> Breadcrumb:
    user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
    breadcrumb = make_topic_breadcrumb(
        main_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic("overview", user_permissions).title(),
    )
    breadcrumb.append(
        BreadcrumbItem(
            title=title,
            url=makeuri_contextless(ctx.request, [], filename="monitor_host_services.py"),
            id="monitor_host_services",
        )
    )
    return breadcrumb
