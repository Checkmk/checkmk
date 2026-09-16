#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_topic_breadcrumb,
)
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.global_settings import (
    central_settings,
    ensure_page_access,
    MatchItemGeneratorSettings,
    render_settings_page,
)
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.search.matchers import MatchItemGeneratorRegistry
from cmk.gui.wato import MainModuleTopicEvents
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.shared_typing.global_settings import GlobalSettingsApp
from cmk.web.utils.urls import makeuri_contextless

from .config_domain import ConfigDomainEventConsole


def register(
    page_registry: PageRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    page_registry.register(PageEndpoint("event_console_settings", _event_console_settings_page))
    match_item_generator_registry.register(
        MatchItemGeneratorSettings(
            "event_console_settings",
            _("Event Console settings"),
            filename="event_console_settings.py",
            shows=_owned_by_the_event_console,
        )
    )


def _owned_by_the_event_console(config_variable: ConfigVariable) -> bool:
    return isinstance(config_variable.primary_domain(), ConfigDomainEventConsole)


def event_console_settings(config: Config) -> GlobalSettingsApp:
    ensure_page_access(config, ["mkeventd.config"])
    if not config.mkeventd_enabled:
        raise MKUserError(None, _('The Event Console is disabled ("omd config").'))
    title = _("Event Console configuration")
    return central_settings(
        config,
        title=title,
        breadcrumb=_breadcrumb(title),
        shows=_owned_by_the_event_console,
    )


def _breadcrumb(title: str) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(
        main_menu_registry.menu_setup(),
        MainModuleTopicEvents.title,
        MainModuleTopicEvents.name,
    )
    breadcrumb.append(
        BreadcrumbItem(
            title=_("Event Console rule packs"),
            url=makeuri_contextless(request, [("mode", "mkeventd_rule_packs")], filename="wato.py"),
            id="mkeventd_rule_packs",
        )
    )
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    return breadcrumb


def _event_console_settings_page(ctx: PageContext) -> None:
    render_settings_page(ctx.config, event_console_settings(ctx.config))
