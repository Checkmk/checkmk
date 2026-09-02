#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from dataclasses import asdict
from typing import cast

from cmk.ccc.site import omd_site
from cmk.ccc.version import edition
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.experimental_flags.global_config import ConfigVariableGroupExperimentalFlags
from cmk.gui.form_specs.visitors import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.mkeventd.wato import (
    ConfigVariableGroupEventConsoleGeneric,
    ConfigVariableGroupEventConsoleLogging,
    ConfigVariableGroupEventConsoleSNMP,
)
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.product_usage_analytics.global_config import (
    ConfigVariableGroupProductUsageAnalytics,
)
from cmk.gui.wato._check_mk_configuration import (
    ConfigVariableGroupCheckExecution,
    ConfigVariableGroupServiceDiscovery,
    ConfigVariableGroupUserManagement,
)
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    ConfigVariable,
    ConfigVariableGroup,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupAIFeatures,
    ConfigVariableGroupDeveloperTools,
    ConfigVariableGroupNotifications,
    ConfigVariableGroupSiteManagement,
    ConfigVariableGroupSupport,
    ConfigVariableGroupUserInterface,
    ConfigVariableGroupWATO,
)
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.utils import site_neutral_path
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing.global_settings import (
    Components,
    GlobalSettingsApp,
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


# TODO Groups defined in edition-specific packages cannot be imported here and are
# referenced by their registry ident instead; they are skipped when the active
# edition does not register them.
_TOPICS: list[tuple[ConfigVariableGroup | str, IconNames, str]] = [
    (
        "Monitoring core",
        IconNames.topic_monitoring,
        "Configures the Checkmk Micro Core, its helpers and check scheduling",
    ),
    (
        "Livestatus proxy",
        IconNames.connection_tests,
        "Configures the Livestatus proxy daemon for connections to remote sites",
    ),
    (
        ConfigVariableGroupServiceDiscovery,
        IconNames.service_discovery,
        "Configures service discovery behavior - how often it runs and how results are treated",
    ),
    (
        ConfigVariableGroupCheckExecution,
        IconNames.check,
        "Configures how checks technically run against hosts",
    ),
    (
        ConfigVariableGroupNotifications,
        IconNames.notifications,
        "Configures global notification system behavior",
    ),
    (
        ConfigVariableGroupEventConsoleGeneric,
        IconNames.snmpmib,
        "Configures general Event Console settings",
    ),
    (
        ConfigVariableGroupEventConsoleLogging,
        IconNames.snmpmib,
        "Configures Event Console logging and diagnostic settings",
    ),
    (
        ConfigVariableGroupEventConsoleSNMP,
        IconNames.snmpmib,
        "Configures how the Event Console receives SNMP traps",
    ),
    (
        "Alert handlers",
        IconNames.alert_handlers,
        "Configures how alert handlers are executed",
    ),
    (
        ConfigVariableGroupUserInterface,
        IconNames.topic_user_interface,
        "Configures broad GUI look, behavior, and performance",
    ),
    (
        "ntopng (chargeable add-on)",
        IconNames.ntop,
        "Configures the connection to ntopng for network flow data",
    ),
    (
        ConfigVariableGroupWATO,
        IconNames.main_setup,
        "Configures behavior of the config workflow itself",
    ),
    (
        ConfigVariableGroupSiteManagement,
        IconNames.sites,
        "Configures distributed monitoring and site connection settings",
    ),
    (
        "Automatic agent updates",
        IconNames.agents,
        "Configures the agent updater and automatic agent deployment",
    ),
    (
        ConfigVariableGroupUserManagement,
        IconNames.users,
        "Configures user/authentication settings",
    ),
    (
        "Reporting",
        IconNames.report,
        "Configures report generation, scheduling and layout defaults",
    ),
    (
        ConfigVariableGroupSupport,
        IconNames.diagnostics,
        "Configures support and diagnostics properties",
    ),
    (
        ConfigVariableGroupDeveloperTools,
        IconNames.developer_resources,
        "Configures internal and experimental developer settings",
    ),
    (
        ConfigVariableGroupAIFeatures,
        IconNames.sparkle,
        "Configures the AI assistant and MCP server integration",
    ),
    (
        ConfigVariableGroupProductUsageAnalytics,
        IconNames.pie_chart,
        "Configures consent and config for anonymized usage",
    ),
    (
        ConfigVariableGroupExperimentalFlags,
        IconNames.release_deploy,
        "Configures temporary auto-generated flags tied to features",
    ),
]


def _make_context(config: Config) -> GlobalSettingsContext:
    return GlobalSettingsContext(
        target_site_id=omd_site(),
        edition_of_local_site=edition(paths.omd_root),
        site_neutral_log_dir=site_neutral_path(paths.log_dir),
        site_neutral_var_dir=site_neutral_path(paths.var_dir),
        configured_sites=config.sites,
        configured_graph_timeranges=config.graph_timeranges,
    )


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
) -> Iterator[GlobalSettingsVariable]:
    for config_variable in group.config_variables():
        varname = config_variable.ident()
        if not _is_shown(config_variable, default_values):
            continue
        form_spec = config_variable.value_model(context)
        assert isinstance(form_spec, FormSpec)
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


def _is_shown(config_variable: ConfigVariable, default_values: dict[str, object]) -> bool:
    return (
        config_variable.in_global_settings()
        and config_variable.primary_domain().enabled()
        and config_variable.primary_domain().in_global_settings
        and config_variable.ident() in default_values
    )


def _topics(config: Config) -> Iterator[GlobalSettingsTopic]:
    context = _make_context(config)
    current_settings = dict(load_configuration_settings())
    default_values = dict(ABCConfigDomain.get_all_default_globals())
    for group_or_ident, icon, subline in _TOPICS:
        group = (
            group_or_ident
            if isinstance(group_or_ident, ConfigVariableGroup)
            else config_variable_group_registry.get(group_or_ident)
        )
        if group is None:
            continue
        variables = list(_variables(group, config, context, current_settings, default_values))
        if not variables:
            continue
        yield GlobalSettingsTopic(
            icon=icon,
            headline=group.title(),
            subline=subline,
            warning=group.warning(),
            variables=variables,
        )


def _app_data(config: Config) -> GlobalSettingsApp:
    return GlobalSettingsApp(
        title=_("Global settings"),
        domain=GlobalSettingsDomain.global_settings,
        scope=GlobalSettingsScopeGlobal(),
        topics=list(_topics(config)),
    )


def _global_settings_page(ctx: PageContext) -> None:
    data = _app_data(ctx.config)
    make_header(
        html,
        title=data.title,
        breadcrumb=Breadcrumb(),
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
    html.show_warning(_("This page is work in progress. It shows a subset of the global settings."))
    html.enable_help_toggle()
    html.vue_component(component_name="cmk-global-settings", data=asdict(data))
    html.footer()
