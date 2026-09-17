#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass
from typing import cast

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version import edition
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.form_specs.visitors import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.global_config import get_global_config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.main_navigation import MainNavigation
from cmk.gui.watolib import read_only
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    ConfigVariable,
    ConfigVariableGroup,
    GlobalSettingsContext,
)
from cmk.gui.watolib.global_settings import (
    effective_site_value,
    effective_value,
    GlobalSettingsOrigin,
    is_available_in_global_settings,
    load_configuration_settings,
    make_global_settings_context,
    may_read,
)
from cmk.gui.watolib.mode import ensure_static_permissions
from cmk.gui.watolib.setup_access import ensure_provider_site, ensure_setup_enabled
from cmk.gui.watolib.sites import load_site_globals, site_management_registry
from cmk.livestatus_client import SiteConfigurations
from cmk.shared_typing.global_settings import (
    Components,
    GlobalLayerValue,
    GlobalScopeValue,
    GlobalSettingsApp,
    GlobalSettingsBreadcrumbItem,
    GlobalSettingsHint,
    GlobalSettingsHintVariant,
    GlobalSettingsScopeGlobal,
    GlobalSettingsScopeSite,
    GlobalSettingsSiteOverride,
    GlobalSettingsTopic,
    GlobalSettingsVariable,
    IconNames,
    SiteScopeValue,
)
from cmk.utils import paths
from cmk.web.utils.flashed_messages import get_flashed_messages_with_categories
from cmk.web.utils.permission_verification import PermissionName
from cmk.web.utils.urls import makeuri_contextless


@dataclass(frozen=True)
class _GlobalScope:
    settings: Mapping[str, object]
    sites: SiteConfigurations


@dataclass(frozen=True)
class _SiteScope:
    site_id: SiteId
    global_settings: Mapping[str, object]
    site_settings: Mapping[str, object]


type _Scope = _GlobalScope | _SiteScope


def ensure_page_access(config: Config, permissions: Iterable[PermissionName]) -> None:
    ensure_setup_enabled(config)
    ensure_provider_site(config)
    ensure_static_permissions(permissions, need_modification_permission=False)


def central_settings(
    config: Config,
    *,
    title: str,
    breadcrumb: Breadcrumb,
    shows: Callable[[ConfigVariable], bool],
) -> GlobalSettingsApp:
    return _app_data(
        config,
        title,
        breadcrumb,
        _GlobalScope(
            settings=load_configuration_settings(),
            sites=site_management_registry["site_management"].load_sites(),
        ),
        shows,
    )


def site_settings(
    config: Config,
    *,
    title: str,
    breadcrumb: Breadcrumb,
    sites: SiteConfigurations,
    site_id: SiteId,
) -> GlobalSettingsApp:
    return _app_data(
        config,
        title,
        breadcrumb,
        _SiteScope(
            site_id=site_id,
            global_settings=load_configuration_settings(),
            site_settings=load_site_globals(sites, site_id),
        ),
        lambda _config_variable: True,
    )


def render_settings_page(config: Config, data: GlobalSettingsApp) -> None:
    MainNavigation.render(config, data.title)
    html.begin_page_content(enable_scrollbar=True)
    for message in get_flashed_messages_with_categories():
        html.show_message_by_msg_type(msg=message.msg, msg_type=message.msg_type, flashed=True)
    if read_only.is_enabled(config.wato_read_only):
        html.show_warning(read_only.message(config.wato_read_only))
    html.vue_component(component_name="cmk-global-settings", data=asdict(data))
    html.footer()


def _app_data(
    config: Config,
    title: str,
    breadcrumb: Breadcrumb,
    scope: _Scope,
    shows: Callable[[ConfigVariable], bool],
) -> GlobalSettingsApp:
    return GlobalSettingsApp(
        title=title,
        breadcrumb=_breadcrumb_items(breadcrumb),
        scope=(
            GlobalSettingsScopeGlobal()
            if isinstance(scope, _GlobalScope)
            else GlobalSettingsScopeSite(site_id=scope.site_id)
        ),
        topics=list(_topics(config, scope, shows)),
    )


def _breadcrumb_items(breadcrumb: Breadcrumb) -> list[GlobalSettingsBreadcrumbItem]:
    return [
        GlobalSettingsBreadcrumbItem(title=str(item.title), link=item.url) for item in breadcrumb
    ]


def _topics(
    config: Config, scope: _Scope, shows: Callable[[ConfigVariable], bool]
) -> Iterator[GlobalSettingsTopic]:
    context = make_global_settings_context(
        edition(paths.omd_root),
        omd_site() if isinstance(scope, _GlobalScope) else scope.site_id,
        sites=config.sites,
        graph_timeranges=config.graph_timeranges,
    )
    default_values = dict(ABCConfigDomain.get_all_default_globals())
    is_activated = get_global_config().global_settings.is_activated
    for group in sorted(config_variable_group_registry.values(), key=lambda g: g.sort_index()):
        variables = list(_variables(group, scope, shows, context, default_values, is_activated))
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


def _variables(
    group: ConfigVariableGroup,
    scope: _Scope,
    shows: Callable[[ConfigVariable], bool],
    context: GlobalSettingsContext,
    default_values: Mapping[str, object],
    is_activated: Callable[[str], bool],
) -> Iterator[GlobalSettingsVariable]:
    for config_variable in group.config_variables():
        varname = config_variable.ident()
        if not shows(config_variable):
            continue
        if not is_available_in_global_settings(
            config_variable, default_values=default_values, is_activated=is_activated
        ):
            continue
        if not may_read(config_variable):
            continue
        form_spec = config_variable.value_model(context)
        visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
        _, vue_factory_value = visitor.to_vue(RawDiskData(default_values[varname]))
        current: GlobalScopeValue | SiteScopeValue
        # Legacy valuespecs render the value into the spec, so the spec has to come from the
        # scope the page edits.
        if isinstance(scope, _GlobalScope):
            value, origin = effective_value(scope.settings, varname)
            spec, vue_value = visitor.to_vue(RawDiskData(value))
            current = GlobalScopeValue(
                value=vue_value,
                explicit=origin is GlobalSettingsOrigin.global_,
                site_overrides=_site_overrides(varname, scope.sites),
            )
        else:
            global_value, global_origin = effective_value(scope.global_settings, varname)
            value, origin = effective_site_value(
                scope.site_settings, varname, global_settings=scope.global_settings
            )
            _, vue_global_value = visitor.to_vue(RawDiskData(global_value))
            spec, vue_value = visitor.to_vue(RawDiskData(value))
            current = SiteScopeValue(
                value=vue_value,
                explicit=origin is GlobalSettingsOrigin.site,
                global_layer=GlobalLayerValue(
                    value=vue_global_value,
                    explicit=global_origin is GlobalSettingsOrigin.global_,
                ),
            )
        yield GlobalSettingsVariable(
            name=varname,
            # The cast is needed twice over: to_vue() statically returns the base
            # FormSpec class, which is not assignable to a union of its concrete
            # subclasses, and the generated global_settings module duplicates the
            # vue_formspec dataclasses instead of importing them, making the
            # visitor output nominally incompatible with Components either way.
            spec=cast(Components, spec),
            factory_value=vue_factory_value,
            current=current,
            hints=[
                GlobalSettingsHint(
                    text=str(hint.text),
                    variant=GlobalSettingsHintVariant(hint.variant),
                    copyable=hint.copyable,
                )
                for hint in config_variable.hints()
            ],
        )


def _site_overrides(varname: str, sites: SiteConfigurations) -> list[GlobalSettingsSiteOverride]:
    return [
        GlobalSettingsSiteOverride(
            site_id=site_id,
            title=site_conf["alias"],
            url=makeuri_contextless(
                request, [("site", site_id)], filename="site_specific_settings.py"
            ),
        )
        for site_id, site_conf in sites.items()
        if varname in site_conf.get("globals", {})
    ]
