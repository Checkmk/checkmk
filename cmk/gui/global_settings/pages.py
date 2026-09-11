#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator
from dataclasses import asdict
from typing import cast

from cmk.ccc.site import omd_site
from cmk.ccc.version import edition
from cmk.gui.breadcrumb import BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.config import Config
from cmk.gui.form_specs.visitors import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.global_config import get_global_config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.main_navigation import MainNavigation
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.watolib import read_only
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    ConfigVariableGroup,
    GlobalSettingsContext,
)
from cmk.gui.watolib.global_settings import (
    is_available_in_global_settings,
    load_configuration_settings,
    make_global_settings_context,
    may_read,
)
from cmk.gui.watolib.mode import ensure_static_permissions
from cmk.gui.watolib.setup_access import ensure_provider_site, ensure_setup_enabled
from cmk.shared_typing.global_settings import (
    Components,
    GlobalSettingsApp,
    GlobalSettingsBreadcrumbItem,
    GlobalSettingsDomain,
    GlobalSettingsScopeGlobal,
    GlobalSettingsSiteOverride,
    GlobalSettingsTopic,
    GlobalSettingsVariable,
    IconNames,
)
from cmk.utils import paths
from cmk.web.utils.urls import makeuri_contextless


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("global_settings", _global_settings_page))


def ensure_permitted(config: Config) -> None:
    ensure_setup_enabled(config)
    ensure_provider_site(config)
    ensure_static_permissions(["wato.global"], need_modification_permission=False)


def _site_overrides(varname: str, config: Config) -> list[GlobalSettingsSiteOverride]:
    return [
        GlobalSettingsSiteOverride(
            site_id=site_id,
            title=site_conf["alias"],
            url=makeuri_contextless(
                request,
                [("mode", "edit_site_globals"), ("site", site_id)],
                filename="wato.py",
            ),
        )
        for site_id, site_conf in config.sites.items()
        if varname in site_conf.get("globals", {})
    ]


def _variables(
    group: ConfigVariableGroup,
    config: Config,
    context: GlobalSettingsContext,
    current_settings: dict[str, object],
    default_values: dict[str, object],
    is_activated: Callable[[str], bool],
) -> Iterator[GlobalSettingsVariable]:
    for config_variable in group.config_variables():
        varname = config_variable.ident()
        if not config_variable.primary_domain().in_global_settings:
            continue
        if not is_available_in_global_settings(
            config_variable, default_values=default_values, is_activated=is_activated
        ):
            continue
        if not may_read(config_variable):
            continue
        form_spec = config_variable.value_model(context)
        visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
        default_value = default_values[varname]
        spec, vue_value = visitor.to_vue(RawDiskData(current_settings.get(varname, default_value)))
        _, vue_default_value = visitor.to_vue(RawDiskData(default_value))
        yield GlobalSettingsVariable(
            name=varname,
            # The cast is needed twice over: to_vue() statically returns the base
            # FormSpec class, which is not assignable to a union of its concrete
            # subclasses, and the generated global_settings module duplicates the
            # vue_formspec dataclasses instead of importing them, making the
            # visitor output nominally incompatible with Components either way.
            spec=cast(Components, spec),
            value=vue_value,
            default_value=vue_default_value,
            modified=varname in current_settings,
            site_overrides=_site_overrides(varname, config),
        )


def _topics(config: Config) -> Iterator[GlobalSettingsTopic]:
    context = make_global_settings_context(
        edition(paths.omd_root),
        omd_site(),
        sites=config.sites,
        graph_timeranges=config.graph_timeranges,
    )
    current_settings = dict(load_configuration_settings())
    default_values = dict(ABCConfigDomain.get_all_default_globals())
    is_activated = get_global_config().global_settings.is_activated
    for group in sorted(config_variable_group_registry.values(), key=lambda g: g.sort_index()):
        variables = list(
            _variables(group, config, context, current_settings, default_values, is_activated)
        )
        if not variables:
            continue
        yield GlobalSettingsTopic(
            # The generated module carries its own copy of the icon enum, so the
            # group's icon is re-created from its value.
            icon=IconNames(group.icon()),
            headline=group.title(),
            subline=group.description(),
            warning=group.warning(),
            variables=variables,
        )


def _breadcrumb_items(title: str) -> list[GlobalSettingsBreadcrumbItem]:
    breadcrumb = make_main_menu_breadcrumb(main_menu_registry.menu_setup())
    breadcrumb.append(BreadcrumbItem(title=title, url=None, id="global_settings"))
    return [
        GlobalSettingsBreadcrumbItem(title=str(item.title), link=item.url) for item in breadcrumb
    ]


def app_data(config: Config) -> GlobalSettingsApp:
    title = _("Global settings")
    return GlobalSettingsApp(
        title=title,
        breadcrumb=_breadcrumb_items(title),
        domain=GlobalSettingsDomain.global_settings,
        scope=GlobalSettingsScopeGlobal(),
        topics=list(_topics(config)),
    )


def _global_settings_page(ctx: PageContext) -> None:
    ensure_permitted(ctx.config)
    data = app_data(ctx.config)
    MainNavigation.render(ctx.config, data.title)
    html.begin_page_content(enable_scrollbar=True)
    if read_only.is_enabled(ctx.config.wato_read_only):
        html.show_warning(read_only.message(ctx.config.wato_read_only))
    html.vue_component(component_name="cmk-global-settings", data=asdict(data))
    html.footer()
