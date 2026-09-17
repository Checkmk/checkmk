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
    GlobalSettingsApp,
    GlobalSettingsBreadcrumbItem,
    GlobalSettingsHint,
    GlobalSettingsHintVariant,
    GlobalSettingsOrigin,
    GlobalSettingsScopeGlobal,
    GlobalSettingsScopeSite,
    GlobalSettingsSiteOverride,
    GlobalSettingsTopic,
    GlobalSettingsVariable,
    IconNames,
)
from cmk.utils import paths
from cmk.web.utils.flashed_messages import get_flashed_messages_with_categories
from cmk.web.utils.permission_verification import PermissionName
from cmk.web.utils.urls import makeuri_contextless


@dataclass(frozen=True)
class _ShownSettings:
    """The settings a page shows and what it takes to render them.

    inherited_settings names the settings the shown ones override; it is None on the
    page that owns them.
    """

    scope: GlobalSettingsScopeGlobal | GlobalSettingsScopeSite
    target_site_id: SiteId
    shows: Callable[[ConfigVariable], bool]
    settings: Mapping[str, object]
    inherited_settings: Mapping[str, object] | None
    override_sites: SiteConfigurations

    def resolve(self, varname: str) -> tuple[object, GlobalSettingsOrigin]:
        if self.inherited_settings is None:
            return effective_value(self.settings, varname)
        return effective_site_value(self.settings, varname, global_settings=self.inherited_settings)


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
        _ShownSettings(
            scope=GlobalSettingsScopeGlobal(),
            target_site_id=omd_site(),
            shows=shows,
            settings=load_configuration_settings(),
            inherited_settings=None,
            override_sites=site_management_registry["site_management"].load_sites(),
        ),
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
        _ShownSettings(
            scope=GlobalSettingsScopeSite(site_id=site_id),
            target_site_id=site_id,
            shows=lambda _config_variable: True,
            settings=load_site_globals(sites, site_id),
            inherited_settings=load_configuration_settings(),
            override_sites=SiteConfigurations({}),
        ),
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
    config: Config, title: str, breadcrumb: Breadcrumb, shown: _ShownSettings
) -> GlobalSettingsApp:
    return GlobalSettingsApp(
        title=title,
        breadcrumb=_breadcrumb_items(breadcrumb),
        scope=shown.scope,
        topics=list(_topics(config, shown)),
    )


def _breadcrumb_items(breadcrumb: Breadcrumb) -> list[GlobalSettingsBreadcrumbItem]:
    return [
        GlobalSettingsBreadcrumbItem(title=str(item.title), link=item.url) for item in breadcrumb
    ]


def _topics(config: Config, shown: _ShownSettings) -> Iterator[GlobalSettingsTopic]:
    context = make_global_settings_context(
        edition(paths.omd_root),
        shown.target_site_id,
        sites=config.sites,
        graph_timeranges=config.graph_timeranges,
    )
    default_values = dict(ABCConfigDomain.get_all_default_globals())
    is_activated = get_global_config().global_settings.is_activated
    for group in sorted(config_variable_group_registry.values(), key=lambda g: g.sort_index()):
        variables = list(_variables(group, shown, context, default_values, is_activated))
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
    shown: _ShownSettings,
    context: GlobalSettingsContext,
    default_values: Mapping[str, object],
    is_activated: Callable[[str], bool],
) -> Iterator[GlobalSettingsVariable]:
    for config_variable in group.config_variables():
        varname = config_variable.ident()
        if not shown.shows(config_variable):
            continue
        if not is_available_in_global_settings(
            config_variable, default_values=default_values, is_activated=is_activated
        ):
            continue
        if not may_read(config_variable):
            continue
        form_spec = config_variable.value_model(context)
        visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
        value, origin = shown.resolve(varname)
        spec, vue_value = visitor.to_vue(RawDiskData(value))
        _, vue_default_value = visitor.to_vue(RawDiskData(default_values[varname]))
        if shown.inherited_settings is None:
            vue_inherited_value = None
        else:
            _, vue_inherited_value = visitor.to_vue(
                RawDiskData(effective_value(shown.inherited_settings, varname)[0])
            )
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
            global_value=vue_inherited_value,
            origin=origin,
            site_overrides=_site_overrides(varname, shown.override_sites),
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
