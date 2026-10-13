#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from functools import partial

from cmk.gui.data_source import data_source_registry
from cmk.gui.http import request
from cmk.gui.painter import CellDrilldown
from cmk.gui.type_defs import (
    ColumnName,
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
from cmk.gui.views.page_edit_view import ColumnDrilldownTarget
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


def column_drilldowns(
    view_spec: ViewSpec,
    column_links: Mapping[int, ContextualLinkEntryConfig],
    context: VisualContext,
    user_permissions: UserPermissions,
) -> dict[int, CellDrilldown]:
    """The drill-downs of an embedded view's columns, by painter index.

    A row of the view is one host or one service, so a link carries that object on top of the
    effective context the view renders with. A row that names less than the target needs, like a
    host downtime for a service view, links nowhere.
    """
    if (
        not column_links
        or (data_source := data_source_registry.get(view_spec["datasource"])) is None
    ):
        return {}
    infos = data_source().infos
    object_infos = [info for info in ("host", "service") if info in infos]
    if not object_infos:
        return {}
    drilldowns: dict[int, CellDrilldown] = {}
    for index, link in column_links.items():
        location = location_from_internal(link["location"])
        if (
            index >= len(view_spec["painters"])
            or (target := _permitted_target(location, user_permissions)) is None
        ):
            continue
        # TODO(CMK-39811): carry the filters a custom column link configures.
        if link["filters"]:
            continue
        drilldowns[index] = CellDrilldown(
            columns=_object_columns(object_infos),
            url=partial(
                _url,
                location,
                context if link["include_context"] else {},
                object_infos,
                [info for info in target["single_infos"] if info in object_infos],
                show_filter_form=link["show_filter_form"],
            ),
        )
    return drilldowns


def inherited_column_link(target: ColumnDrilldownTarget) -> ContextualLinkEntryConfig:
    """The stored link of a column the view editor set to drill down to the target."""
    return ContextualLinkEntryConfig(
        title=target[1],
        location=target,
        filters=[],
        include_context=True,
        include_time_range=True,
        show_filter_form=False,
    )


def column_drilldown_targets(
    column_links: Mapping[int, ContextualLinkEntryConfig],
) -> dict[int, ColumnDrilldownTarget]:
    """The targets of the inherited column links, as the view editor shows them."""
    return {
        index: (link["location"][0], link["location"][1])
        for index, link in column_links.items()
        if not link["filters"]
    }


def _object_columns(object_infos: Sequence[InfoName]) -> list[ColumnName]:
    return ["host_name", "service_description"] if "service" in object_infos else ["host_name"]


def _permitted_target(location: VisualLocation, user_permissions: UserPermissions) -> Visual | None:
    if location.owner is None:
        return resolved_copy(location, user_permissions)
    return permitted_copies(location, user_permissions).get(location.owner)


def _object_key(
    row: Row, object_infos: Sequence[InfoName]
) -> dict[FilterName, FilterHTTPVariables]:
    """The filters naming the row's object, as the Vue object widgets carry them.

    A row of a data source of hosts and services may be about a host alone, with an empty service.
    """
    key: dict[FilterName, FilterHTTPVariables] = {"siteopt": {"site": str(row["site"])}}
    if host_name := row["host_name"]:
        key["host"] = {"host": str(host_name)}
    if "service" in object_infos and (service_description := row["service_description"]):
        key["service"] = {"service": str(service_description)}
    return key


def _url(
    location: VisualLocation,
    context: VisualContext,
    object_infos: Sequence[InfoName],
    target_infos: Sequence[InfoName],
    row: Row,
    *,
    show_filter_form: bool,
) -> str | None:
    object_key = _object_key(row, object_infos)
    # The filters of the object key are named after the infos they fill.
    if any(info not in object_key for info in target_infos):
        return None
    page, name_variable = _PAGE_BY_TARGET_TYPE[location.type]
    variables = {name_variable: location.name}
    # Without an owner, the target page resolves the name for each viewer.
    if location.owner is not None:
        variables["owner"] = str(location.owner)
    # The clicked object goes last, so it wins over the same filter in the context.
    for filter_variables in {**context, **object_key}.values():
        variables.update(filter_variables)
    variables["filled_in"] = "filter"
    variables["_show_filter_form"] = "1" if show_filter_form else "0"
    return makeuri_contextless(request, list(variables.items()), filename=page)
