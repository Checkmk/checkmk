#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from itertools import chain

from cmk.gui.hooks import request_memoize
from cmk.gui.http import request
from cmk.gui.plugins.visuals.utils import (
    active_filter_flag,
    collect_filters,
    Filter,
    filter_registry,
    get_livestatus_filter_headers,
    get_only_sites_from_context,
    visual_info_registry,
)
from cmk.gui.type_defs import FilterName, InfoName, SingleInfos, Visual, VisualContext

from ._filter_valuespecs import VisualFilterListWithAddPopup


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
