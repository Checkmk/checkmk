#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict
from typing import override
from urllib.parse import urlencode

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import edition
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.config import Config
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.monitor.command import (
    acknowledge_presets_url,
    downtime_presets_url,
    DowntimeRecurrences,
    MonitorCommands,
    notification_rules_url,
)
from cmk.gui.monitor.hosts._pages._monitor_all_hosts import monitor_all_hosts_visual_spec
from cmk.gui.monitor.services._ai_explain import ai_explain
from cmk.gui.monitor.services._page_menu import build_page_menu, HostMenus
from cmk.gui.pages import Page, PageContext
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.monitoring.host_services import (
    DowntimeRecurrence,
    Edition,
    MonitoringAction,
    MonitoringHostServicesApp,
    MonitoringPageLinkButton,
    RowAction,
)
from cmk.utils import paths
from cmk.web.utils.urls import makeuri_contextless

_SUPPORTED_ACTIONS: tuple[str, ...] = (
    "acknowledge",
    "reschedule",
    "schedule_downtimes",
)

_LEGACY_VIEW_NAME = "host"
_LEGACY_VIEW_PERMISSION = f"view.{_LEGACY_VIEW_NAME}"

_HOST_STATUS_VIEW_NAME = "hoststatus"
_ALL_HOSTS_PERMISSION = "view.allhosts"
_RULESETS_PERMISSION = "wato.rulesets"


def _row_actions(config: Config, hostname: HostName) -> list[RowAction]:
    """The links a row offers on the service it shows.

    The host is the page, so it is part of the address already; the service is not, and travels as
    the `{service}` placeholder the listing resolves per row - the same shape the hosts listing
    uses for `{host}`.
    """
    if not config.wato_enabled or not user.may(_RULESETS_PERMISSION):
        return []
    return [
        RowAction(
            ident="parameters",
            title=_("Parameters"),
            icon="rulesets",
            url=f"wato.py?{urlencode([('mode', 'object_parameters'), ('host', hostname)])}"
            "&service={service}",
        )
    ]


class MonitorHostServicesPage(Page):
    def __init__(
        self,
        commands: MonitorCommands,
        recurrences: DowntimeRecurrences,
        host_menus: HostMenus,
    ) -> None:
        self._commands = commands
        self._recurrences = recurrences
        self._host_menus = host_menus

    def _permitted_actions(self) -> list[MonitoringAction]:
        return [
            MonitoringAction(ident=command.ident, title=str(command.title), icon=command.icon)
            for command in self._commands.permitted_actions(user, "service", _SUPPORTED_ACTIONS)
        ]

    @override
    def page(self, ctx: PageContext) -> None:
        user.need_permission(_LEGACY_VIEW_PERMISSION)

        hostname = ctx.request.get_validated_type_input_mandatory(HostName, "host")
        site_id = SiteId(ctx.request.get_str_input_mandatory("site"))
        title = _("Services of host %(host)s") % {"host": hostname}

        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
        breadcrumb = _make_breadcrumb(ctx, hostname, site_id, user_permissions)

        make_header(
            html,
            title=str(title),
            breadcrumb=breadcrumb,
            page_menu=build_page_menu(
                host_menus=self._host_menus,
                hostname=hostname,
                site_id=site_id,
                breadcrumb=breadcrumb,
            ),
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

        html.vue_component(
            "cmk-monitoring-host-services",
            data=asdict(
                MonitoringHostServicesApp(
                    poll_interval_ms=ctx.config.view_option_refreshes[0] * 1000,
                    may_ignore_hard_limit=user.may("general.ignore_hard_limit"),
                    host=hostname,
                    site=site_id,
                    user_id=str(user.id),
                    edition=Edition(edition(paths.omd_root).short),
                    ai_explain=ai_explain.is_enabled(),
                    actions=self._permitted_actions(),
                    downtime_recurrences=[
                        DowntimeRecurrence(recur=recurrence.recur, title=recurrence.title)
                        for recurrence in self._recurrences.offered()
                    ],
                    row_actions=_row_actions(ctx.config, hostname),
                    acknowledge_presets_url=acknowledge_presets_url(ctx.config),
                    notification_rules_url=notification_rules_url(ctx.config),
                    downtime_presets_url=downtime_presets_url(ctx.config),
                    legacy_view_button=MonitoringPageLinkButton(
                        url=makeuri_contextless(
                            ctx.request,
                            [
                                ("view_name", _LEGACY_VIEW_NAME),
                                ("host", hostname),
                                ("site", site_id),
                            ],
                            filename="view.py",
                        ),
                        title=_("Return to classic view"),
                    ),
                )
            ),
        )

        ai_explain.render_listener()

        html.footer()


def _host_url(ctx: PageContext, hostname: HostName, site_id: SiteId) -> str:
    """Where the host itself is shown: the all hosts listing with its panel open.

    The panel is named in the fragment, the way the listing writes it when a user
    opens one, so going up from a service lands on the host it belongs to rather
    than on a listing the user has to find it in again. A user who may not see
    that listing keeps the classic host status view.
    """
    if not user.may(_ALL_HOSTS_PERMISSION):
        return makeuri_contextless(
            ctx.request,
            [("view_name", _HOST_STATUS_VIEW_NAME), ("host", hostname), ("site", site_id)],
            filename="view.py",
        )
    panel = urlencode([("host", hostname), ("site", site_id)])
    return f"{makeuri_contextless(ctx.request, [], filename='monitor_all_hosts.py')}#{panel}"


def _make_breadcrumb(
    ctx: PageContext,
    hostname: HostName,
    site_id: SiteId,
    user_permissions: UserPermissions,
) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(
        main_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic("overview", user_permissions).title(),
    )
    if user.may(_ALL_HOSTS_PERMISSION):
        breadcrumb.append(
            BreadcrumbItem(
                title=str(monitor_all_hosts_visual_spec()["title"]),
                url=makeuri_contextless(ctx.request, [], filename="monitor_all_hosts.py"),
                id="monitor_all_hosts",
            )
        )
    breadcrumb.append(
        BreadcrumbItem(
            title=hostname,
            url=_host_url(ctx, hostname, site_id),
            id=None,
        )
    )
    breadcrumb.append(
        BreadcrumbItem(
            title=_("Services of host"),
            url=makeuri_contextless(
                ctx.request,
                [("host", hostname), ("site", site_id)],
                filename="monitor_host_services.py",
            ),
            id="monitor_host_services",
        )
    )
    return breadcrumb
