#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.ccc import store

from cmk.utils import paths

from cmk.gui import hooks, utils
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.type_defs import FilterHTTPVariables
from cmk.gui.valuespec import AutocompleterRegistry

from . import _filters, _site_filters, info
from ._add_to_visual import (
    add_to_dashboard_choices_autocompleter,
    ajax_add_visual,
    ajax_popup_add,
)
from ._add_to_visual import get_visual_choices as get_visual_choices
from ._add_to_visual import page_menu_dropdown_add_to_visual as page_menu_dropdown_add_to_visual
from ._add_to_visual import page_menu_topic_add_to as page_menu_topic_add_to
from ._add_to_visual import set_page_context as set_page_context
from ._breadcrumb import visual_page_breadcrumb as visual_page_breadcrumb
from ._filter_context import active_context_from_request as active_context_from_request
from ._filter_context import collect_filters as collect_filters
from ._filter_context import context_to_uri_vars as context_to_uri_vars
from ._filter_context import filters_of_visual as filters_of_visual
from ._filter_context import get_context_from_uri_vars as get_context_from_uri_vars
from ._filter_context import get_filter as get_filter
from ._filter_context import get_link_filter_names as get_link_filter_names
from ._filter_context import get_merged_context as get_merged_context
from ._filter_context import get_missing_single_infos as get_missing_single_infos
from ._filter_context import (
    get_missing_single_infos_group_aware as get_missing_single_infos_group_aware,
)
from ._filter_context import get_single_info_keys as get_single_info_keys
from ._filter_context import get_singlecontext_vars as get_singlecontext_vars
from ._filter_context import info_params as info_params
from ._filter_context import missing_context_filters as missing_context_filters
from ._filter_context import visible_filters_of_visual as visible_filters_of_visual
from ._filter_form import render_filter_form as render_filter_form
from ._filter_form import show_filter_form as show_filter_form
from ._filter_valuespecs import FilterChoices as FilterChoices
from ._filter_valuespecs import filters_allowed_for_info as filters_allowed_for_info
from ._filter_valuespecs import filters_allowed_for_infos as filters_allowed_for_infos
from ._filter_valuespecs import filters_exist_for_infos as filters_exist_for_infos
from ._filter_valuespecs import PageAjaxVisualFilterListGetChoice
from ._filter_valuespecs import VisualFilterList as VisualFilterList
from ._filter_valuespecs import VisualFilterListWithAddPopup as VisualFilterListWithAddPopup
from ._livestatus import get_filter_headers as get_filter_headers
from ._livestatus import get_livestatus_filter_headers as get_livestatus_filter_headers
from ._livestatus import get_only_sites_from_context as get_only_sites_from_context
from ._livestatus import livestatus_query_bare as livestatus_query_bare
from ._livestatus import livestatus_query_bare_string as livestatus_query_bare_string
from ._page_create_visual import page_create_visual as page_create_visual
from ._page_create_visual import SingleInfoSelection as SingleInfoSelection
from ._page_edit_visual import get_context_specs as get_context_specs
from ._page_edit_visual import page_edit_visual as page_edit_visual
from ._page_edit_visual import process_context_specs as process_context_specs
from ._page_edit_visual import render_context_specs as render_context_specs
from ._page_edit_visual import single_infos_spec as single_infos_spec
from ._page_list import page_list as page_list
from ._permissions import declare_visual_permissions as declare_visual_permissions
from ._site_filters import default_site_filter_heading_info as default_site_filter_heading_info
from ._site_filters import SiteFilter as SiteFilter
from ._store import available as available
from ._store import available_by_owner as available_by_owner
from ._store import declare_custom_permissions as declare_custom_permissions
from ._store import declare_packaged_visuals_permissions as declare_packaged_visuals_permissions
from ._store import get_permissioned_visual as get_permissioned_visual
from ._store import invalidate_all_caches
from ._store import load as load
from ._store import load_visuals_of_a_user as load_visuals_of_a_user
from ._store import save as save
from ._store import TVisual as TVisual
from ._title import view_title as view_title
from ._title import visual_title as visual_title
from .filter import (
    Filter,
    filter_registry,
    FilterOption,
    FilterRegistry,
    FilterTime,
    InputTextFilter,
)
from .info import visual_info_registry, VisualInfo, VisualInfoRegistry
from .type import visual_type_registry, VisualType


def register(
    page_registry: PageRegistry,
    _visual_info_registry: VisualInfoRegistry,
    _filter_registry: FilterRegistry,
    autocompleter_registry: AutocompleterRegistry,
    site_choices: Callable[[], list[tuple[str, str]]],
    site_filter_heading_info: Callable[[FilterHTTPVariables], str | None],
) -> None:
    page_registry.register(
        PageEndpoint("ajax_visual_filter_list_get_choice", PageAjaxVisualFilterListGetChoice)
    )
    page_registry.register(PageEndpoint("ajax_popup_add_visual", ajax_popup_add))
    page_registry.register(PageEndpoint("ajax_add_visual", ajax_add_visual))
    info.register(_visual_info_registry)
    _filters.register(page_registry, filter_registry)
    _site_filters.register(
        filter_registry, autocompleter_registry, site_choices, site_filter_heading_info
    )
    autocompleter_registry.register_autocompleter(
        "add_to_dashboard_choices", add_to_dashboard_choices_autocompleter
    )

    hooks.register_builtin("snapshot-pushed", invalidate_all_caches)
    hooks.register_builtin(
        "snapshot-pushed", lambda: store.clear_pickled_files_cache(paths.tmp_dir)
    )
    hooks.register_builtin("users-saved", lambda x: invalidate_all_caches())


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("visuals", globals())


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by built-in and also 3rd party plugins.

    Our built-in plug-in have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plug-ins for now.

    In the moment we define an official plug-in API, we can drop this and require all plug-ins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plug-in loading order
    import cmk.gui.plugins.visuals as api_module  # pylint: disable=cmk-module-layer-violation
    import cmk.gui.plugins.visuals.utils as plugin_utils  # pylint: disable=cmk-module-layer-violation

    for name, val in (
        ("Filter", Filter),
        ("filter_registry", filter_registry),
        ("FilterOption", FilterOption),
        ("FilterTime", FilterTime),
        ("InputTextFilter", InputTextFilter),
        ("get_only_sites_from_context", get_only_sites_from_context),
        ("visual_info_registry", visual_info_registry),
        ("visual_type_registry", visual_type_registry),
        ("VisualInfo", VisualInfo),
        ("VisualType", VisualType),
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name] = val
