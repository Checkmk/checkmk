#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Iterable
from typing import Any, Literal

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.exceptions import MKUserError
from cmk.gui.type_defs import FilterHeader, VisualContext
from cmk.gui.utils.user_errors import user_errors

from ._filter_context import collect_filters
from .filter import Filter


# Compute Livestatus-Filters based on a given context. Returns
# the only_sites list and a string with the filter headers
# TODO: Untangle only_sites and filter headers
# TODO: Reduce redundancies with filters_of_visual()
def get_filter_headers(
    infos: Container[str], context: VisualContext
) -> tuple[str, list[SiteId] | None]:
    filter_headers = "".join(get_livestatus_filter_headers(context, collect_filters(infos)))
    return filter_headers, get_only_sites_from_context(context)


def get_only_sites_from_context(context: VisualContext) -> list[SiteId] | None:
    """Gather possible existing "only sites" information from context

    We need to deal with all possible site filters (sites, site and siteopt).

    VisualContext is structured like this:

    {"site": {"site": "sitename"}}
    {"siteopt": {"site": "sitename"}}
    {"sites": {"sites": "sitename|second"}}

    The difference is no fault or "old" data structure. We can have both kind of structures.
    These are the data structure the visuals work with.

    "site" and "sites" are conflicting filters. The new optional filter
    "sites" for many sites filter is only used if the view is configured
    to only this filter.
    """
    if "sites" in context and (only_sites := context["sites"]["sites"]):
        return [SiteId(site) for site in only_sites.strip().split("|") if site]

    for var in ["site", "siteopt"]:
        if site_name := context.get(var, {}).get("site"):
            return [SiteId(site_name)]
    return None


# TODO: When this is used by the reporting then *all* filters are active.
# That way the inventory data will always be loaded. When we convert this to the
# visuals principle the we need to optimize this.
def get_livestatus_filter_headers(
    context: VisualContext, filters: Iterable[Filter]
) -> Iterable[FilterHeader]:
    """Prepare Filter headers for Livestatus"""
    for filt in filters:
        try:
            value = context.get(filt.ident, {})
            filt.validate_value(value)
            if header := filt.filter(value):
                yield header
        except MKUserError as e:
            user_errors.add(e)


def livestatus_query_bare_string(
    table: Literal["host", "service"],
    context: VisualContext,
    columns: Iterable[str],
    cache: Literal["reload"] | None = None,
) -> str:
    """Return for the service table filtered by context the given columns.
    Optional cache reload. Return with site info in"""
    infos = {"host": ["host"], "service": ["host", "service"]}.get(table, [])
    filters = collect_filters(infos)
    filterheaders = "".join(get_livestatus_filter_headers(context, filters))

    # optimization: avoid query with unconstrained result
    if not filterheaders and not get_only_sites_from_context(context):
        return ""
    query = ["GET %ss" % table, "Columns: %s" % " ".join(columns), filterheaders]
    if cache:
        query.insert(1, f"Cache: {cache}")

    return "\n".join(query)


def livestatus_query_bare(
    table: Literal["host", "service"],
    context: VisualContext,
    columns: list[str],
    cache: Literal["reload"] | None = None,
) -> list[dict[str, Any]]:
    """Return for the service table filtered by context the given columns.
    Optional cache reload. Return with site info in"""
    if query := livestatus_query_bare_string(table, context, columns, cache):
        selected_sites = get_only_sites_from_context(context)
        res_columns = ["site"] + columns
        with sites.only_sites(selected_sites), sites.prepend_site():
            return [dict(zip(res_columns, row)) for row in sites.live().query(query)]

    return []
