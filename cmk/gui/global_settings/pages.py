#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.site import SiteId
from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_topic_breadcrumb,
)
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.global_settings.search import MatchItemGeneratorSettings
from cmk.gui.global_settings.utils import (
    central_settings,
    ensure_page_access,
    render_settings_page,
    site_settings,
)
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.search.matchers import MatchItemGeneratorRegistry
from cmk.gui.site_config import has_distributed_setup_remote_sites
from cmk.gui.wato import MainModuleTopicGeneral
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.gui.watolib.sites import (
    site_globals_editable,
    site_management_registry,
    STATIC_PERMISSIONS_SITES,
)
from cmk.livestatus_client import SiteConfigurations
from cmk.shared_typing.global_settings import GlobalSettingsApp
from cmk.web.utils.urls import makeuri_contextless


def register(
    page_registry: PageRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    page_registry.register(PageEndpoint("global_settings", _global_settings_page))
    page_registry.register(PageEndpoint("site_specific_settings", _site_specific_settings_page))
    match_item_generator_registry.register(
        MatchItemGeneratorSettings(
            "global_settings",
            _("Global settings"),
            filename="global_settings.py",
            shows=_shown_on_the_global_page,
        )
    )


def _shown_on_the_global_page(config_variable: ConfigVariable) -> bool:
    return config_variable.primary_domain().in_global_settings


def global_settings(config: Config) -> GlobalSettingsApp:
    ensure_page_access(config, ["wato.global"])
    title = _("Global settings")
    return central_settings(
        config,
        title=title,
        breadcrumb=_global_breadcrumb(title),
        shows=_shown_on_the_global_page,
    )


def site_specific_settings(config: Config, site_id: SiteId) -> GlobalSettingsApp:
    ensure_page_access(config, STATIC_PERMISSIONS_SITES)
    sites = site_management_registry["site_management"].load_sites()
    if site_id not in sites:
        raise MKUserError("site", _("This site does not exist."))
    if not site_globals_editable(sites, sites[site_id]):
        raise MKUserError("site", _not_editable_message(sites))
    title = _("Site-specific settings of %(alias)s") % {"alias": sites[site_id]["alias"]}
    return site_settings(
        config,
        title=title,
        breadcrumb=_site_specific_breadcrumb(site_id, title),
        sites=sites,
        site_id=site_id,
    )


def _not_editable_message(sites: SiteConfigurations) -> str:
    if not has_distributed_setup_remote_sites(sites):
        return _("You cannot configure site-specific settings in non-distributed setups.")
    return _(
        "This site is not the central site nor a replication remote site."
        " You cannot configure specific settings for it."
    )


def _global_breadcrumb(title: str) -> Breadcrumb:
    breadcrumb = _setup_breadcrumb()
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    return breadcrumb


def _site_specific_breadcrumb(site_id: SiteId, title: str) -> Breadcrumb:
    breadcrumb = _setup_breadcrumb()
    breadcrumb.append(
        BreadcrumbItem(
            title=_("Distributed monitoring"),
            url=makeuri_contextless(request, [("mode", "sites")], filename="wato.py"),
            id="sites",
        )
    )
    breadcrumb.append(
        BreadcrumbItem(
            title=_("Edit site connection %(site_id)s") % {"site_id": site_id},
            url=makeuri_contextless(
                request, [("mode", "edit_site"), ("site", site_id)], filename="wato.py"
            ),
            id="edit_site",
        )
    )
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    return breadcrumb


def _setup_breadcrumb() -> Breadcrumb:
    return make_topic_breadcrumb(
        main_menu_registry.menu_setup(),
        MainModuleTopicGeneral.title,
        MainModuleTopicGeneral.name,
    )


def _global_settings_page(ctx: PageContext) -> None:
    data = global_settings(ctx.config)
    render_settings_page(ctx.config, data)


def _site_specific_settings_page(ctx: PageContext) -> None:
    site_id = SiteId(request.get_ascii_input_mandatory("site"))
    data = site_specific_settings(ctx.config, site_id)
    render_settings_page(ctx.config, data)
