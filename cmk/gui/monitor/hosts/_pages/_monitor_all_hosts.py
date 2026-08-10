#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict
from typing import override

from cmk.ccc.user import UserId
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.config import Config
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
from cmk.gui.pages import Page, PageContext
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import DynamicIconName, IconNames, StaticIcon, Visual
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.views.command.registry import CommandRegistry
from cmk.shared_typing.monitoring.all_hosts import (
    MonitoringAllHostsApp,
    MonitoringPageLinkButton,
    RowAction,
)

from ._actions import PermittedHostActions

_PAGE_TITLE = _("All hosts (experimental)")

_LEGACY_VIEW_NAME = "allhosts"
_LEGACY_VIEW_PERMISSION = f"view.{_LEGACY_VIEW_NAME}"


def _row_actions(config: Config) -> list[RowAction]:
    if not config.wato_enabled:
        return []
    actions: list[RowAction] = []
    if user.may("wato.use") and (user.may("wato.seeall") or user.may("wato.hosts")):
        actions.append(
            RowAction(
                ident="edit",
                title=_("Edit host"),
                icon="edit",
                url="wato.py?mode=edit_host&host={host}",
            )
        )
    if user.may("wato.rulesets"):
        actions.append(
            RowAction(
                ident="parameters",
                title=_("Parameters"),
                icon="rulesets",
                url="wato.py?mode=object_parameters&host={host}",
            )
        )
    return actions


_SUPPORTED_ACTIONS: tuple[str, ...] = (
    "acknowledge",
    "schedule_downtimes",
    "reschedule",
)


def monitor_all_hosts_visual_spec() -> Visual:
    return {
        "owner": UserId.builtin(),
        "description": "",
        "hidebutton": False,
        "public": True,
        "topic": "overview",
        "title": _PAGE_TITLE,
        "name": "monitor_all_hosts",
        "sort_index": 21,
        "is_show_more": False,
        "icon": DynamicIconName("folder"),
        "hidden": False,
        "single_infos": [],
        "context": {},
        "link_from": {},
        "add_context_to_title": True,
        "packaged": False,
        "main_menu_search_terms": [],
    }


class MonitorAllHostsPage(Page):
    def __init__(self, commands: CommandRegistry) -> None:
        self._commands = commands

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
        )

        html.vue_component(
            "cmk-monitoring-all-hosts",
            data=asdict(
                MonitoringAllHostsApp(
                    poll_interval_ms=ctx.config.view_option_refreshes[0] * 1000,
                    actions=PermittedHostActions(
                        self._commands, user, _SUPPORTED_ACTIONS
                    ).as_models(),
                    row_actions=_row_actions(ctx.config),
                    may_ignore_hard_limit=user.may("general.ignore_hard_limit"),
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

        html.footer()


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


def _availability_dropdowns() -> list[PageMenuDropdown]:
    if not user.may("general.see_availability"):
        return []

    availability_url = makeuri_contextless(
        request,
        [("view_name", _LEGACY_VIEW_NAME), ("mode", "availability")],
        filename="view.py",
    )

    return [
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
    ]


def _build_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    menu = PageMenu(
        dropdowns=_availability_dropdowns(),
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
