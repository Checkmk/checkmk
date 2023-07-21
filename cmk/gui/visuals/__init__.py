#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import utils
from cmk.gui.pages import PageRegistry

from . import info
from ._add_to_visual import ajax_add_visual, ajax_popup_add
from ._add_to_visual import page_menu_dropdown_add_to_visual as page_menu_dropdown_add_to_visual
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
from ._store import available as available
from ._store import declare_custom_permissions as declare_custom_permissions
from ._store import declare_packaged_visuals_permissions as declare_packaged_visuals_permissions
from ._store import delete_local_file, get_installed_packages
from ._store import get_permissioned_visual as get_permissioned_visual
from ._store import load as load
from ._store import load_visuals_of_a_user as load_visuals_of_a_user
from ._store import local_file_exists, move_visual_to_local
from ._store import save as save
from ._store import TVisual as TVisual
from ._title import view_title as view_title
from ._title import visual_title as visual_title
from .filter import Filter, filter_registry, FilterOption, FilterTime, InputTextFilter
from .info import visual_info_registry, VisualInfo, VisualInfoRegistry
from .type import visual_type_registry, VisualType


def register(page_registry: PageRegistry, _visual_info_registry: VisualInfoRegistry) -> None:
    page_registry.register_page("ajax_visual_filter_list_get_choice")(
        PageAjaxVisualFilterListGetChoice
    )
    page_registry.register_page_handler("ajax_popup_add_visual", ajax_popup_add)
    page_registry.register_page_handler("ajax_add_visual", ajax_add_visual)
    info.register(_visual_info_registry)


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("visuals", globals())


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.plugins.visuals as api_module
    import cmk.gui.plugins.visuals.utils as plugin_utils

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
