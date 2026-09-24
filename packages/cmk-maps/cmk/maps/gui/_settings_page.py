#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The module-near settings page of Checkmk Maps.

Setup → Global settings does not list the Maps settings
(:class:`ConfigDomainMaps` sets ``in_global_settings = False``), so this page owns
their central values, the way the Event Console settings page owns the Event
Console's. It renders the global settings editor, which saves each value through
the global settings REST API, with one topic per Maps config variable group.
"""

from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_main_menu_breadcrumb,
)
from cmk.gui.config import Config
from cmk.gui.global_settings import central_settings, ensure_page_access, render_settings_page
from cmk.gui.i18n import _
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.maps.gui._config_domain import ConfigDomainMaps
from cmk.shared_typing.global_settings import GlobalSettingsApp

SETTINGS_URL = "maps_settings.py"
_MAPS_HOME_URL = "maps.py"


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("maps_settings", _maps_settings_page))


def maps_settings(config: Config) -> GlobalSettingsApp:
    ensure_page_access(config, [ConfigDomainMaps.global_settings_permission])
    title = _("Maps settings")
    return central_settings(
        config,
        title=title,
        breadcrumb=_breadcrumb(title),
        shows=_owned_by_maps,
    )


def _owned_by_maps(config_variable: ConfigVariable) -> bool:
    return isinstance(config_variable.primary_domain(), ConfigDomainMaps)


def _breadcrumb(title: str) -> Breadcrumb:
    # Maps has no Setup tile; its pages hang under Customize → Maps.
    breadcrumb = make_main_menu_breadcrumb(main_menu_registry.menu_customize())
    breadcrumb.append(BreadcrumbItem(title=_("Maps"), url=_MAPS_HOME_URL, id="maps"))
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    return breadcrumb


def _maps_settings_page(ctx: PageContext) -> None:
    render_settings_page(ctx.config, maps_settings(ctx.config))
