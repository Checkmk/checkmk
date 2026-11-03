#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict
from typing import override

from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId
from cmk.ccc.version import edition
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.monitor.command import (
    acknowledge_defaults,
    acknowledge_presets_url,
    downtime_presets,
    downtime_presets_url,
    DowntimeRecurrences,
    host_setup_links,
    HOST_SUPPORTED_ACTIONS,
    MonitorCommands,
    notification_rules_url,
)
from cmk.gui.monitor.export import EXPORT_EVENT, MonitorExportMenu
from cmk.gui.monitor.services._ai_explain import ai_explain
from cmk.gui.monitor.services._api._limits import LIMIT_TIERS
from cmk.gui.monitor.services._supported_actions import SERVICE_SUPPORTED_ACTIONS
from cmk.gui.page_menu import PageMenu
from cmk.gui.pages import Page, PageContext
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.type_defs import Visual
from cmk.gui.user_sites import sorted_sites
from cmk.shared_typing.monitoring.all_services import (
    AcknowledgeDefaults,
    DowntimePreset,
    DowntimeRecurrence,
    DowntimeUntilKeyword,
    Edition,
    MonitoringAction,
    MonitoringAllServicesApp,
    MonitoringPageLinkButton,
    RowAction,
    Site,
)
from cmk.utils import paths
from cmk.web.utils.icons import DynamicIconName
from cmk.web.utils.urls import makeuri_contextless

_PAGE_TITLE = _l("All services")

_LEGACY_VIEW_NAME = "allservices"
_LEGACY_VIEW_PERMISSION = f"view.{_LEGACY_VIEW_NAME}"


def monitor_all_services_visual_spec() -> Visual:
    return {
        "owner": UserId.builtin(),
        "description": "",
        "hidebutton": False,
        "public": True,
        "topic": "overview",
        "title": _PAGE_TITLE,
        "name": "monitor_all_services",
        "sort_index": 25,
        "is_show_more": False,
        "icon": DynamicIconName("services"),
        "hidden": False,
        "single_infos": [],
        "context": {},
        "link_from": {},
        "add_context_to_title": True,
        "packaged": False,
        "main_menu_search_terms": [],
    }


class MonitorAllServicesPage(Page):
    def __init__(
        self,
        commands: MonitorCommands,
        recurrences: DowntimeRecurrences,
        teleport_target: str | None = None,
    ) -> None:
        self._commands = commands
        self._recurrences = recurrences
        self._teleport_target = teleport_target

    @override
    def page(self, ctx: PageContext) -> None:
        user.need_permission(_LEGACY_VIEW_PERMISSION)

        breadcrumb = _make_breadcrumb(ctx)

        make_header(
            html,
            title=str(_PAGE_TITLE),
            breadcrumb=breadcrumb,
            page_menu=_build_page_menu(breadcrumb),
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

        ack = acknowledge_defaults(ctx.config)

        html.vue_component(
            "cmk-monitoring-all-services",
            data=asdict(
                MonitoringAllServicesApp(
                    poll_interval_ms=ctx.config.view_option_refreshes[0] * 1000,
                    user_id=str(user.id),
                    site=str(omd_site()),
                    sites=[
                        Site(id=str(site_id), alias=alias)
                        for site_id, alias in sorted_sites(ctx.config.sites)
                    ],
                    edition=Edition(edition(paths.omd_root).short),
                    header_teleport_target=self._teleport_target,
                    ai_explain=ai_explain.is_enabled(),
                    export_event=EXPORT_EVENT,
                    actions=[
                        MonitoringAction(
                            ident=command.ident, title=str(command.title), icon=command.icon
                        )
                        for command in self._commands.permitted_actions(
                            user, "service", SERVICE_SUPPORTED_ACTIONS
                        )
                    ],
                    host_actions=[
                        MonitoringAction(
                            ident=command.ident, title=str(command.title), icon=command.icon
                        )
                        for command in self._commands.permitted_actions(
                            user, "host", HOST_SUPPORTED_ACTIONS
                        )
                    ],
                    host_row_actions=[
                        RowAction(ident=link.ident, title=link.title, icon=link.icon, url=link.url)
                        for link in host_setup_links(ctx.config, user)
                    ],
                    downtime_recurrences=[
                        DowntimeRecurrence(recur=recurrence.recur, title=recurrence.title)
                        for recurrence in self._recurrences.offered()
                    ],
                    may_ignore_hard_limit=user.may("general.ignore_hard_limit"),
                    limit_tiers=list(LIMIT_TIERS),
                    acknowledge_presets_url=acknowledge_presets_url(ctx.config),
                    acknowledge_defaults=AcknowledgeDefaults(
                        sticky=ack.sticky,
                        persistent=ack.persistent,
                        notify=ack.notify,
                        expire_seconds=ack.expire_seconds,
                    ),
                    downtime_presets=[
                        DowntimePreset(
                            title=preset.title,
                            end=(
                                preset.end
                                if isinstance(preset.end, int)
                                else DowntimeUntilKeyword(preset.end)
                            ),
                        )
                        for preset in downtime_presets(ctx.config)
                    ],
                    notification_rules_url=notification_rules_url(ctx.config),
                    downtime_presets_url=downtime_presets_url(ctx.config),
                    legacy_view_button=MonitoringPageLinkButton(
                        url=makeuri_contextless(
                            ctx.request,
                            vars_=[("view_name", _LEGACY_VIEW_NAME)],
                            filename="view.py",
                        ),
                        title=_("Return to classic view"),
                    ),
                )
            ),
        )

        ai_explain.render_listener()

        html.footer()


def _make_breadcrumb(ctx: PageContext) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(
        main_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic("overview", ctx.user_permissions).title(),
    )
    breadcrumb.append(
        BreadcrumbItem(
            title=_PAGE_TITLE,
            url=makeuri_contextless(ctx.request, [], filename="monitor_all_services.py"),
            id="monitor_all_services",
        )
    )
    return breadcrumb


def _build_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    menu = PageMenu(dropdowns=MonitorExportMenu().dropdowns(), breadcrumb=breadcrumb)
    for topic in menu["help"].topics:
        topic.entries = [e for e in topic.entries if e.name != "inline_help"]
    return menu
