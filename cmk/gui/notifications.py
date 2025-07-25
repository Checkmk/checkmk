#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import NamedTuple, override

from livestatus import LivestatusResponse, MKLivestatusNotFoundError

import cmk.gui.pages
import cmk.utils.render
from cmk.gui import sites
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import active_config, Config
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKAuthException
from cmk.gui.htmllib.header import make_header
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
from cmk.gui.pages import Page, PageEndpoint, PageRegistry
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    PermissionSection,
    PermissionSectionRegistry,
)
from cmk.gui.table import table_element
from cmk.gui.user_async_replication import user_profile_async_replication_page
from cmk.gui.utils.flashed_messages import get_flashed_messages
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri
from cmk.gui.watolib.user_scripts import declare_notification_plugin_permissions
from cmk.gui.watolib.users import get_enabled_remote_sites_for_logged_in_user


def register(
    page_registry: PageRegistry, permission_section_registry: PermissionSectionRegistry
) -> None:
    page_registry.register(PageEndpoint("clear_failed_notifications", ClearFailedNotificationPage))
    permission_section_registry.register(PERMISSION_SECTION_NOTIFICATION_PLUGINS)


class FailedNotificationTimes(NamedTuple):
    acknowledged_unitl: float
    modified: float


g_columns: list[str] = [
    "time",
    "contact_name",
    "command_name",
    "host_name",
    "service_description",
    "comment",
]

PERMISSION_SECTION_NOTIFICATION_PLUGINS = PermissionSection(
    name="notification_plugin",
    title=_("Notification plug-ins"),
    do_sort=True,
)


def load_plugins() -> None:
    """Plug-in initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    declare_dynamic_permissions(declare_notification_plugin_permissions)


def _acknowledge_failed_notifications(timestamp: float, now: float) -> None:
    """Set the acknowledgement time for the current user"""
    g.failed_notification_times = FailedNotificationTimes(timestamp, now)
    user.acknowledged_notifications = int(timestamp)


def acknowledged_time() -> float:
    """Returns the timestamp to start looking for failed notifications for the current user"""
    times: FailedNotificationTimes | None = g.get("failed_notification_times")

    # Initialize the request cache "g.failed_notification_times" from the user profile in case it is
    # needed. Either on first call to this function or when the file on disk was modified.
    if times is None or user.file_modified("acknowledged_notifications") > times.modified:
        now = time.time()
        user_time = user.acknowledged_notifications

        if user_time == 0:
            # When this timestamp is first initialized, save the current timestamp as the
            # acknowledge date. This should considerably reduce the number of log files that have to
            # be searched when retrieving the list
            _acknowledge_failed_notifications(now, now)
        else:
            g.failed_notification_times = FailedNotificationTimes(
                user.acknowledged_notifications, now
            )

    return g.failed_notification_times.acknowledged_unitl  # type: ignore[no-any-return]


def number_of_failed_notifications(after: float | None) -> int:
    if not _may_see_failed_notifications():
        return 0

    query_txt = _failed_notification_query(
        before=None, after=after, extra_headers=None, stat_only=True
    )

    try:
        result: int = sites.live().query_summed_stats(query_txt)[0]
    except MKLivestatusNotFoundError:
        result = 0  # Normalize the result when no site answered

    if result == 0 and not sites.live().dead_sites():
        # In case there are no errors and all sites are reachable:
        # advance the users acknowledgement time
        now = time.time()
        _acknowledge_failed_notifications(now, now)

    return result


def load_failed_notifications(
    before: float | None = None,
    after: float | None = None,
    extra_headers: str | None = None,
) -> LivestatusResponse:
    may_see_notifications = _may_see_failed_notifications()
    if not may_see_notifications:
        return LivestatusResponse([])

    return sites.live().query(
        _failed_notification_query(before, after, extra_headers, stat_only=False)
    )


def _failed_notification_query(
    before: float | None,
    after: float | None,
    extra_headers: str | None = None,
    *,
    stat_only: bool,
) -> str:
    query = ["GET log"]
    if stat_only:
        query.append("Stats: log_state != 0")
    else:
        query.append("Columns: %s" % " ".join(g_columns))
        query.append("Filter: log_state != 0")

    query.extend(
        [
            "Filter: class = 3",
            "Filter: log_type = SERVICE NOTIFICATION RESULT",
            "Filter: log_type = HOST NOTIFICATION RESULT",
            "Or: 2",
        ]
    )

    if before is not None:
        query.append("Filter: time <= %d" % before)
    if after is not None:
        query.append("Filter: time >= %d" % after)

    if user.may("general.see_failed_notifications"):
        horizon = active_config.failed_notification_horizon
    else:
        horizon = 86400
    query.append("Filter: time > %d" % (int(time.time()) - horizon))

    query_txt = "\n".join(query)

    if extra_headers is not None:
        query_txt += extra_headers

    return query_txt


def _may_see_failed_notifications() -> bool:
    return user.may("general.see_failed_notifications") or user.may(
        "general.see_failed_notifications_24h"
    )


class ClearFailedNotificationPage(Page):
    def __init__(self) -> None:
        if not _may_see_failed_notifications():
            raise MKAuthException(_("You are not allowed to view the failed notifications."))

    @override
    def page(self, config: Config) -> None:
        acktime = request.get_float_input_mandatory("acktime", time.time())
        if request.var("_confirm"):
            _acknowledge_failed_notifications(acktime, time.time())

            if get_enabled_remote_sites_for_logged_in_user(user, config.sites):
                title = _("Replicate user profile")
                breadcrumb = make_simple_page_breadcrumb(
                    main_menu_registry.menu_monitoring(), title
                )
                make_header(html, title, breadcrumb)

                for message in get_flashed_messages():
                    html.show_message(message.msg)
                user_profile_async_replication_page(back_url="clear_failed_notifications.py")
                return

        failed_notifications = load_failed_notifications(before=acktime, after=acknowledged_time())
        self._show_page(acktime, failed_notifications)
        if request.var("_confirm"):
            html.reload_whole_page()

    # TODO: We should really recode this to use the view and a normal view command / action
    def _show_page(self, acktime: float, failed_notifications: LivestatusResponse) -> None:
        title = _("Confirm failed notifications")
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_monitoring(), title)

        page_menu = self._page_menu(acktime, failed_notifications, breadcrumb)

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
                                    icon_name="save",
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
