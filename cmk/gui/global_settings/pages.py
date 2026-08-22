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
from cmk.gui.form_specs.visitors import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigVariable,
    ConfigVariableGroup,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupDeveloperTools,
    ConfigVariableGroupSiteManagement,
)
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.utils import site_neutral_path
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing.global_settings import (
    Components,
    GlobalSettingsApp,
    GlobalSettingsDomain,
    GlobalSettingsScopeGlobal,
    GlobalSettingsTopic,
    GlobalSettingsVariable,
    IconNames,
)
from cmk.utils import paths


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("global_settings", _global_settings_page))


_TOPICS: list[tuple[ConfigVariableGroup, IconNames, str]] = [
    (
        ConfigVariableGroupSiteManagement,
        IconNames.configuration,
        "Settings that control the behavior of this site",
    ),
    (
        ConfigVariableGroupDeveloperTools,
        IconNames.development,
        "Settings for developing Checkmk",
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
        yield GlobalSettingsVariable(
            name=varname,
            # The cast is needed twice over: to_vue() statically returns the base
            # FormSpec class, which is not assignable to a union of its concrete
            # subclasses, and the generated global_settings module duplicates the
            # vue_formspec dataclasses instead of importing them, making the
            # visitor output nominally incompatible with Components either way.
            spec=cast(Components, spec),
            value=vue_value,
            modified=varname in current_settings,
        )


def _is_shown(config_variable: ConfigVariable, default_values: dict[str, object]) -> bool:
    return (
        config_variable.in_global_settings()
        and config_variable.primary_domain().enabled()
        and config_variable.primary_domain().in_global_settings
        and config_variable.ident() in default_values
    )


def _app_data(config: Config) -> GlobalSettingsApp:
    context = _make_context(config)
    current_settings = dict(load_configuration_settings())
    default_values = dict(ABCConfigDomain.get_all_default_globals())
    return GlobalSettingsApp(
        title=_("Global settings"),
        domain=GlobalSettingsDomain.global_settings,
        scope=GlobalSettingsScopeGlobal(),
        topics=[
            GlobalSettingsTopic(
                icon=icon,
                headline=group.title(),
                subline=subline,
                warning=group.warning(),
                variables=list(
                    _variables(group, config, context, current_settings, default_values)
                ),
            )
            for group, icon, subline in _TOPICS
        ],
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
    html.show_warning(
        _(
            "This page is work in progress. It shows a subset of the global settings "
            "and changes made here are not saved."
        )
    )
    html.vue_component(component_name="cmk-global-settings", data=asdict(data))
    html.footer()
