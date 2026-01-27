#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import override

from livestatus import LivestatusResponse

import cmk.utils.render
from cmk.gui import sites
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.exceptions import MKAuthException
from cmk.gui.htmllib.header import make_header
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
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    PermissionSection,
    PermissionSectionRegistry,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.user_async_replication import user_profile_async_replication_page
from cmk.gui.utils.flashed_messages import get_flashed_messages
from cmk.gui.utils.notifications import (
    acknowledge_failed_notifications,
    acknowledged_time,
    failed_notification_query,
    g_columns,
    may_see_failed_notifications,
)
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri
from cmk.gui.watolib.user_scripts import declare_notification_plugin_permissions
from cmk.gui.watolib.users import get_enabled_remote_sites_for_logged_in_user


def register(
    page_registry: PageRegistry, permission_section_registry: PermissionSectionRegistry
) -> None:
    page_registry.register(
        PageEndpoint("clear_failed_notifications", ClearFailedNotificationPage())
    )
    permission_section_registry.register(PERMISSION_SECTION_NOTIFICATION_PLUGINS)
    declare_dynamic_permissions(declare_notification_plugin_permissions)


PERMISSION_SECTION_NOTIFICATION_PLUGINS = PermissionSection(
    name="notification_plugin",
    title=_("Notification plug-ins"),
    do_sort=True,
)


class ClearFailedNotificationPage(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        if not may_see_failed_notifications():
            raise MKAuthException(_("You are not allowed to view the failed notifications."))

        acktime = ctx.request.get_float_input_mandatory("acktime", time.time())
        if ctx.request.var("_confirm"):
            acknowledge_failed_notifications(acktime, time.time())

            if get_enabled_remote_sites_for_logged_in_user(user, ctx.config.sites):
                title = _("Replicate user profile")
                breadcrumb = make_simple_page_breadcrumb(
                    main_menu_registry.menu_monitoring(), title
                )
                make_header(html, title, breadcrumb)

                for message in get_flashed_messages():
                    html.show_message(message.msg)
                user_profile_async_replication_page(back_url="clear_failed_notifications.py")
                return

        failed_notifications = _load_failed_notifications(before=acktime, after=acknowledged_time())
        self._show_page(ctx.request, acktime, failed_notifications)
        if ctx.request.var("_confirm"):
            html.reload_whole_page()

    # TODO: We should really recode this to use the view and a normal view command / action
    def _show_page(
        self, request: Request, acktime: float, failed_notifications: LivestatusResponse
    ) -> None:
        title = _("Confirm failed notifications")
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_monitoring(), title)

        page_menu = self._page_menu(request, acktime, failed_notifications, breadcrumb)

        make_header(html, title, breadcrumb, page_menu)

        self._show_notification_table(failed_notifications)

        html.footer()

    def _show_notification_table(self, failed_notifications: LivestatusResponse) -> None:
        with table_element() as table:
            header = {name: idx for idx, name in enumerate(g_columns)}
            for row in failed_notifications:
                table.row()
                table.cell(
                    _("Time"),
                    cmk.utils.render.approx_age(time.time() - row[header["time"]]),
                )
                table.cell(_("Contact"), row[header["contact_name"]])
                table.cell(_("Plug-in"), row[header["command_name"]])
                table.cell(_("Host"), row[header["host_name"]])
                table.cell(_("Service"), row[header["service_description"]])
                table.cell(_("Output"), row[header["comment"]])

    def _page_menu(
        self,
        request: Request,
        acktime: float,
        failed_notifications: LivestatusResponse,
        breadcrumb: Breadcrumb,
    ) -> PageMenu:
        confirm_url = make_simple_link(
            make_confirm_delete_link(
                url=makeactionuri(
                    request,
                    transactions,
                    [("acktime", str(acktime)), ("_confirm", "1")],
                ),
                title=_("Acknowledge all failed notifications"),
                message=("Up to: %s") % cmk.utils.render.date_and_time(acktime),
                confirm_button=_("Acknowledge"),
            )
        )

        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Actions"),
                    topics=[
                        PageMenuTopic(
                            title=_("Actions"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Acknowledge"),
                                    icon_name=StaticIcon(IconNames.save),
                                    item=confirm_url,
                                    is_shortcut=True,
                                    is_suggested=True,
                                    is_enabled=bool(failed_notifications),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )


def _load_failed_notifications(
    before: float | None,
    after: float,
    extra_headers: str | None = None,
) -> LivestatusResponse:
    may_see_notifications = may_see_failed_notifications()
    if not may_see_notifications:
        return LivestatusResponse([])

    return sites.live().query(
        failed_notification_query(before, after, extra_headers, stat_only=False)
    )
