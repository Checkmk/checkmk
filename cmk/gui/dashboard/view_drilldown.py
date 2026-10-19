#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import partial

from cmk.gui.data_source import data_source_registry
from cmk.gui.http import request
from cmk.gui.painter import CellDrilldown
from cmk.gui.type_defs import (
    ColumnName,
    ContextFilterConfig,
    ContextualLinkEntryConfig,
    ContextualLinkTargetType,
    FilterHTTPVariables,
    FilterName,
    InfoName,
    Row,
    ViewSpec,
    Visual,
    VisualContext,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.drilldown_filters import drilldown_filters, filter_drilldown
from cmk.gui.visuals import get_single_info_keys, missing_context_filters
from cmk.gui.visuals.filter.drilldowns import Drilldown
from cmk.web.utils.urls import makeuri_contextless

from .api.model.contextual_link import (
    location_from_internal,
    permitted_copies,
    resolved_copy,
    VisualLocation,
)

_PAGE_BY_TARGET_TYPE: Mapping[ContextualLinkTargetType, tuple[str, str]] = {
    "views": ("view.py", "view_name"),
    "dashboards": ("dashboard.py", "name"),
}


@dataclass(frozen=True)
class _CarriedFilter:
    drilldown: Drilldown
    keys: Sequence[str]


def column_drilldowns(
    view_spec: ViewSpec,
    column_links: Mapping[int, ContextualLinkEntryConfig],
    context: VisualContext,
    user_permissions: UserPermissions,
) -> dict[int, CellDrilldown]:
    """The drill-downs of an embedded view's columns, by painter index."""
    if (
        not column_links
        or (data_source_type := data_source_registry.get(view_spec["datasource"])) is None
    ):
        return {}
    data_source = data_source_type()
    object_infos = [info for info in ("host", "service") if info in data_source.infos]
    drilldowns: dict[int, CellDrilldown] = {}
    for index, link in column_links.items():
        location = location_from_internal(link["location"])
        if (
            index >= len(view_spec["painters"])
            or (target := _permitted_target(location, user_permissions)) is None
        ):
            continue
        link_context = context if link["include_context"] else {}
        if link["filters"]:
            carriable = set(drilldown_filters(data_source, location.type))
            carried = {
                filter_name: _CarriedFilter(drilldown, keys)
                for filter_name, keys in _filter_keys(link["filters"]).items()
                if filter_name in carriable
                and (drilldown := filter_drilldown(filter_name)) is not None
            }
            if not carried:
                continue
            drilldowns[index] = CellDrilldown(
                columns=[
                    column
                    for carried_filter in carried.values()
                    for column in carried_filter.drilldown.columns
                ],
                url=partial(
                    _custom_url,
                    location,
                    link_context,
                    carried,
                    set(get_single_info_keys(target["single_infos"])),
                    show_filter_form=link["show_filter_form"],
                ),
            )
        elif object_infos:
            drilldowns[index] = CellDrilldown(
                columns=_object_columns(object_infos),
                url=partial(
                    _inherited_url,
                    location,
                    link_context,
                    object_infos,
                    [info for info in target["single_infos"] if info in object_infos],
                    show_filter_form=link["show_filter_form"],
                ),
            )
    return drilldowns


def _object_columns(object_infos: Sequence[InfoName]) -> list[ColumnName]:
    return ["host_name", "service_description"] if "service" in object_infos else ["host_name"]


def _permitted_target(location: VisualLocation, user_permissions: UserPermissions) -> Visual | None:
    if location.owner is None:
        return resolved_copy(location, user_permissions)
    return permitted_copies(location, user_permissions).get(location.owner)


def _object_filters(
    row: Row, object_infos: Sequence[InfoName]
) -> dict[FilterName, FilterHTTPVariables]:
    """The filters naming the row's object, as the Vue object widgets carry them.

    A row of a data source of hosts and services may be about a host alone, with an empty service.
    """
    filters: dict[FilterName, FilterHTTPVariables] = {"siteopt": {"site": str(row["site"])}}
    if host_name := row["host_name"]:
        filters["host"] = {"host": str(host_name)}
    if "service" in object_infos and (service_description := row["service_description"]):
        filters["service"] = {"service": str(service_description)}
    return filters


def _inherited_url(
    location: VisualLocation,
    context: VisualContext,
    object_infos: Sequence[InfoName],
    target_infos: Sequence[InfoName],
    row: Row,
    *,
    show_filter_form: bool,
) -> str | None:
    object_filters = _object_filters(row, object_infos)
    # The object filters are named after the infos they fill.
    if any(info not in object_filters for info in target_infos):
        return None
    # The clicked object goes last, so it wins over the same filter in the context.
    return _target_url(location, {**context, **object_filters}, show_filter_form=show_filter_form)


def _filter_keys(filters: Sequence[ContextFilterConfig]) -> dict[FilterName, list[str]]:
    filter_keys: dict[FilterName, list[str]] = {}
    for filter_config in filters:
        keys = filter_keys.setdefault(filter_config["filter_id"], [])
        if "key" in filter_config:
            keys.append(filter_config["key"])
    return filter_keys


def _custom_url(
    location: VisualLocation,
    context: VisualContext,
    carried: Mapping[FilterName, _CarriedFilter],
    single_info_keys: set[FilterName],
    row: Row,
    *,
    show_filter_form: bool,
) -> str | None:
    valued = {
        filter_name: variables
        for filter_name, carried_filter in carried.items()
        if (variables := carried_filter.drilldown.variables(row, carried_filter.keys)) is not None
    }
    filters = {**context, **valued}
    if missing_context_filters(single_info_keys, filters):
        return None
    return _target_url(location, filters, show_filter_form=show_filter_form)


def _target_url(location: VisualLocation, context: VisualContext, *, show_filter_form: bool) -> str:
    page, name_variable = _PAGE_BY_TARGET_TYPE[location.type]
    variables: dict[str, str] = {}
    for filter_variables in context.values():
        variables.update(filter_variables)
    # The target's own variables go last, so no filter can override them.
    variables[name_variable] = location.name
    # Without an owner, the target page resolves the name for each viewer.
    if location.owner is not None:
        variables["owner"] = str(location.owner)
    variables["filled_in"] = "filter"
    variables["_show_filter_form"] = "1" if show_filter_form else "0"
    return makeuri_contextless(request, list(variables.items()), filename=page)
