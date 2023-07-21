#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import copy
import json
import os
import pickle
import re
import sys
import traceback
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import suppress
from itertools import chain
from pathlib import Path
from typing import Any, cast, Final, Generic, get_args, TypeVar

from livestatus import LivestatusTestingError

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.packaging import PackageName
from cmk.utils.user import UserId

import cmk.gui.forms as forms
import cmk.gui.pagetypes as pagetypes
import cmk.gui.query_filters as query_filters
import cmk.gui.userdb as userdb
import cmk.gui.utils as utils
from cmk.gui import hooks
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.config import active_config, default_authorized_builtin_role_ids
from cmk.gui.ctx_stack import g
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import HTMLContent
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.log import logger
from cmk.gui.logged_in import save_user_file, user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    doc_reference_to_page_menu,
    make_javascript_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuTopic,
)
from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import declare_permission, permission_registry
from cmk.gui.plugins.visuals.utils import (
    active_filter_flag,
    collect_filters,
    Filter,
    filter_registry,
    filters_allowed_for_info,
    filters_allowed_for_infos,
    get_livestatus_filter_headers,
    get_only_sites_from_context,
    visual_info_registry,
    visual_type_registry,
    VisualType,
)
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import (
    FilterHTTPVariables,
    FilterName,
    HTTPVariables,
    Icon,
    InfoName,
    PermissionName,
    SingleInfos,
    ViewSpec,
    Visual,
    VisualContext,
    VisualName,
    VisualTypeName,
)
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import is_user_with_publish_permissions, user_may
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    file_name_and_query_vars_from_url,
    make_confirm_delete_link,
    make_confirm_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
    urlencode,
)
from cmk.gui.validate import validate_id
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    DEF_VALUE,
    Dictionary,
    DropdownChoice,
    DualListChoice,
    FixedValue,
    GroupedListOfMultipleChoices,
    IconSelector,
    Integer,
    JSONValue,
    ListOfMultiple,
    ListOfMultipleChoiceGroup,
    TextAreaUnicode,
    TextInput,
    Transform,
    ValueSpec,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
    ValueSpecValidateFunc,
)

from ._add_to_visual import ajax_add_visual, ajax_popup_add
from ._add_to_visual import page_menu_dropdown_add_to_visual as page_menu_dropdown_add_to_visual
from ._add_to_visual import set_page_context as set_page_context
from ._breadcrumb import visual_page_breadcrumb as visual_page_breadcrumb
from ._filter_form import render_filter_form as render_filter_form
from ._filter_form import show_filter_form as show_filter_form
from ._filter_valuespecs import FilterChoices as FilterChoices
from ._filter_valuespecs import PageAjaxVisualFilterListGetChoice
from ._filter_valuespecs import VisualFilterList as VisualFilterList
from ._filter_valuespecs import VisualFilterListWithAddPopup as VisualFilterListWithAddPopup
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


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("ajax_visual_filter_list_get_choice")(
        PageAjaxVisualFilterListGetChoice
    )
    page_registry.register_page_handler("ajax_popup_add_visual", ajax_popup_add)
    page_registry.register_page_handler("ajax_add_visual", ajax_add_visual)


#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


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

    for name in (
        "Filter",
        "filter_registry",
        "FilterOption",
        "FilterTime",
        "get_only_sites_from_context",
        "visual_info_registry",
        "visual_type_registry",
        "VisualInfo",
        "VisualType",
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name]


# .
#   .--Filters-------------------------------------------------------------.
#   |                     _____ _ _ _                                      |
#   |                    |  ___(_) | |_ ___ _ __ ___                       |
#   |                    | |_  | | | __/ _ \ '__/ __|                      |
#   |                    |  _| | | | ||  __/ |  \__ \                      |
#   |                    |_|   |_|_|\__\___|_|  |___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def get_filter(name: str) -> Filter:
    """Returns the filter object identified by the given name
    Raises a KeyError in case a not existing filter is requested."""
    return filter_registry[name]


# For all single_infos which are configured for a view which datasource
# does not provide these infos, try to match the keys of the single_info
# attributes to a filter which can then be used to filter the data of
# the available infos.
# This is needed to make the "hostgroup" single_info possible on datasources
# which do not have the "hostgroup" info, but the "host" info. This
# is some kind of filter translation between a filter of the "hostgroup" info
# and the "hosts" info.
def get_link_filter_names(
    single_infos: SingleInfos,
    info_keys: SingleInfos,
    link_filters: dict[FilterName, FilterName],
) -> Iterator[tuple[FilterName, FilterName]]:
    for info_key in single_infos:
        if info_key not in info_keys:
            for key in info_params(info_key):
                if key in link_filters:
                    yield key, link_filters[key]


def filters_of_visual(
    visual: Visual,
    info_keys: SingleInfos,
    link_filters: dict[FilterName, FilterName] | None = None,
) -> list[Filter]:
    """Collects all filters to be used for the given visual"""
    if link_filters is None:
        link_filters = {}

    filters: dict[FilterName, Filter] = {}
    for info_key in info_keys:
        if info_key in visual["single_infos"]:
            for key in info_params(info_key):
                filters[key] = get_filter(key)
            continue

        for key, val in visual["context"].items():
            if isinstance(val, dict):  # this is a real filter
                try:
                    filters[key] = get_filter(key)
                except KeyError:
                    pass  # Silently ignore not existing filters

    # See get_link_filter_names() comment for details
    for key, dst_key in get_link_filter_names(visual["single_infos"], info_keys, link_filters):
        filters[dst_key] = get_filter(dst_key)

    # add ubiquitary_filters that are possible for these infos
    for fn in get_ubiquitary_filters():
        # Disable 'wato_folder' filter, if Setup is disabled or there is a single host view
        filter_ = get_filter(fn)

        if fn == "wato_folder" and (not filter_.available() or "host" in visual["single_infos"]):
            continue
        if not filter_.info or filter_.info in info_keys:
            filters[fn] = filter_

    return list(filters.values())


# TODO: Cleanup this special case
def get_ubiquitary_filters() -> list[FilterName]:
    return ["wato_folder"]


# Reduces the list of the visuals used filters. The result are the ones
# which are really presented to the user later.
# For the moment we only remove the single context filters which have a
# hard coded default value which is treated as enforced value.
def visible_filters_of_visual(visual: Visual, use_filters: list[Filter]) -> list[Filter]:
    show_filters = []

    single_keys = get_single_info_keys(visual["single_infos"])

    for f in use_filters:
        if f.ident not in single_keys or not visual["context"].get(f.ident):
            show_filters.append(f)

    return show_filters


def context_to_uri_vars(context: VisualContext) -> list[tuple[str, str]]:
    """Produce key/value tuples for HTTP variables from the visual context"""
    return list(chain.from_iterable(filter_vars.items() for filter_vars in context.values()))


# Vice versa: find all filters that belong to the current URI variables
# and create a context dictionary from that.
def get_context_from_uri_vars(only_infos: SingleInfos | None = None) -> VisualContext:
    context = {}
    for filter_name, filter_object in filter_registry.items():
        if only_infos is not None and filter_object.info not in only_infos:
            continue  # Skip filters related to not relevant infos

        this_filter_vars = {}
        for varname in filter_object.htmlvars:
            if not request.has_var(varname):
                continue  # Variable to set in environment

            filter_value = request.get_str_input_mandatory(varname)
            if not filter_value:
                continue

            this_filter_vars[varname] = filter_value

        if this_filter_vars:
            context[filter_name] = this_filter_vars

    return context


def get_merged_context(*contexts: VisualContext) -> VisualContext:
    """Merges multiple filter contexts to a single one

    The last context that sets a filter wins. The intended order is to provide contexts in
    "descending order", e.g. like this for dashboards:

    1. URL context
    2. Dashboard context
    3. Dashlet context
    """
    return {key: value for context in contexts for key, value in context.items()}


# Compute Livestatus-Filters based on a given context. Returns
# the only_sites list and a string with the filter headers
# TODO: Untangle only_sites and filter headers
# TODO: Reduce redundancies with filters_of_visual()
def get_filter_headers(table, infos, context: VisualContext):  # type: ignore[no-untyped-def]
    filter_headers = "".join(get_livestatus_filter_headers(context, collect_filters(infos)))
    return filter_headers, get_only_sites_from_context(context)


def active_context_from_request(infos: SingleInfos, context: VisualContext) -> VisualContext:
    vs_filterlist = VisualFilterListWithAddPopup(info_list=infos)
    if request.has_var("_active"):
        return vs_filterlist.from_html_vars("")

    # Test if filters are in url and rescostruct them. This is because we
    # contruct crosslinks manually without the filter menu.
    # We must merge with the view context as many views have defaults, which
    # are not included in the crosslink.
    if flag := active_filter_flag(set(vs_filterlist._filters.keys()), request.itervars()):
        with request.stashed_vars():
            request.set_var("_active", flag)
            return get_merged_context(context, vs_filterlist.from_html_vars(""))
    return context


# .
#   .--Misc----------------------------------------------------------------.
#   |                          __  __ _                                    |
#   |                         |  \/  (_)___  ___                           |
#   |                         | |\/| | / __|/ __|                          |
#   |                         | |  | | \__ \ (__                           |
#   |                         |_|  |_|_|___/\___|                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def get_missing_single_infos(single_infos: SingleInfos, context: VisualContext) -> set[FilterName]:
    return missing_context_filters(get_single_info_keys(single_infos), context)


def missing_context_filters(
    require_filters: set[FilterName], context: VisualContext
) -> set[FilterName]:
    set_filters = (
        filter_name
        for filter_name, filter_context in context.items()
        if any(filter_context.values())
    )

    return require_filters.difference(set_filters)


def visual_title(
    what: str,
    visual: Visual,
    context: VisualContext,
    skip_title_context: bool = False,
) -> str:
    title = _u(str(visual["title"]))

    # In case we have a site context given replace the $SITE$ macro in the titles.
    site_filter_vars = context.get("site", {})
    assert isinstance(site_filter_vars, dict)
    title = title.replace("$SITE$", site_filter_vars.get("site", ""))

    if visual["add_context_to_title"] and not skip_title_context:
        title = _add_context_title(context, visual["single_infos"], title)

    return title


def view_title(view_spec: ViewSpec, context: VisualContext) -> str:
    return visual_title("view", view_spec, context)


def _add_context_title(context: VisualContext, single_infos: Sequence[str], title: str) -> str:
    def filter_heading(
        filter_name: FilterName,
        filter_vars: FilterHTTPVariables,
    ) -> str | None:
        try:
            filt = get_filter(filter_name)
        except KeyError:
            return ""  # silently ignore not existing filters

        return filt.heading_info(filter_vars)

    extra_titles = [v for v in get_singlecontext_vars(context, single_infos).values() if v]

    # FIXME: Is this really only needed for visuals without single infos?
    if not single_infos:
        for filter_name, filt_vars in context.items():
            if heading := filter_heading(filter_name, filt_vars):
                extra_titles.append(heading)

    if extra_titles:
        title += " " + ", ".join(extra_titles)

    for fn in get_ubiquitary_filters():
        # Disable 'wato_folder' filter, if Setup is disabled or there is a single host view
        if fn == "wato_folder" and (not active_config.wato_enabled or "host" in single_infos):
            continue

        if heading := filter_heading(fn, context.get(fn, {})):
            title = heading + " - " + title

    return title


# Determines the names of HTML variables to be set in order to
# specify a specify row in a datasource with a certain info.
# Example: the info "history" (Event Console History) needs
# the variables "event_id" and "history_line" to be set in order
# to exactly specify one history entry.
@request_memoize()
def info_params(info_key: InfoName) -> list[FilterName]:
    return [key for key, _vs in visual_info_registry[info_key]().single_spec]


def get_single_info_keys(single_infos: SingleInfos) -> set[FilterName]:
    return set(chain.from_iterable(map(info_params, single_infos)))


def get_singlecontext_vars(context: VisualContext, single_infos: SingleInfos) -> dict[str, str]:
    # Link filters only happen when switching from (host/service)group
    # datasource to host/service datasource. As this function is datasource
    # unaware we optionally test for this posibility when (host/service)group
    # is a single info.
    link_filters = {
        "hostgroup": "opthostgroup",
        "servicegroup": "optservicegroup",
    }

    def var_value(filter_name: FilterName) -> str:
        if filter_vars := context.get(filter_name):
            if filt := filter_registry.get(filter_name):
                return filter_vars.get(filt.htmlvars[0], "")
        return ""

    return {
        key: var_value(key) or var_value(link_filters.get(key, ""))
        for key in get_single_info_keys(single_infos)
    }
