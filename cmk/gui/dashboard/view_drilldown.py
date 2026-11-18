#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import partial

from cmk.gui.data_source import ABCDataSource, data_source_registry
from cmk.gui.http import request
from cmk.gui.painter import CellDrilldown
from cmk.gui.top_heading import DRILLED_FROM_VAR
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
from cmk.gui.views.drilldown_filters import (
    drilldown_filters,
    Dropped,
    DROPPED_FILTERS_VAR,
    dropped_filters_variable,
    filter_keys,
    row_drilldown,
    row_has_columns,
)
from cmk.gui.visual_link import may_add_site_hint
from cmk.gui.visuals import get_single_info_keys
from cmk.gui.visuals.filter.drilldowns import Drilldown
from cmk.gui.visuals.info import visual_info_registry
from cmk.shared_typing.drill_up_button import DrillUpButton
from cmk.web.utils.urls import makeuri_contextless

from .api.model.contextual_link import location_from_internal, resolved_copy, VisualLocation


@dataclass(frozen=True)
class TimeRangeVariables:
    """The URL variables that carry a dashboard's time range, as the dashboard wrote them."""

    from_: str
    to: str


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
    context: VisualContext,
    user_permissions: UserPermissions,
    drilled_from: DrillUpButton | None = None,
) -> dict[int, CellDrilldown]:
    """The drill-downs of an embedded view's columns, by painter index."""
    if (
        not any(painter.column_link for painter in view_spec["painters"])
        or (data_source_type := data_source_registry.get(view_spec["datasource"])) is None
    ):
        return {}
    data_source = data_source_type()
    object_infos = [info for info in ("host", "service") if info in data_source.infos]
    drilldowns: dict[int, CellDrilldown] = {}
    for index, painter in enumerate(view_spec["painters"]):
        if (link := painter.column_link) is None:
            continue
        location = location_from_internal(link["location"])
        if (target := resolved_copy(location, user_permissions)) is None:
            continue
        link_context = context if link["include_context"] else {}
        joined = painter.column_type == "join_column"
        if link["filters"]:
            drilldowns[index] = _filter_drilldown(
                data_source,
                location,
                link,
                link_context,
                filter_keys(link["filters"]),
                joined=joined,
                drilled_from=drilled_from,
                carries_site=False,
            )
        elif object_infos and not _takes_another_object(data_source, target):
            drilldowns[index] = _inherited_drilldown(
                location,
                target,
                link,
                link_context,
                object_infos,
                joined=joined,
                drilled_from=drilled_from,
            )
        else:
            # A row of another object, such as a host group, carries that object.
            row_filters = _row_object_filters(data_source, location.type, target["single_infos"])
            drilldowns[index] = _filter_drilldown(
                data_source,
                location,
                link,
                link_context,
                {name: [] for name in row_filters},
                joined=joined,
                drilled_from=drilled_from,
                carries_site=_carries_site(target, row_filters),
            )
    return drilldowns


def _filter_drilldown(
    data_source: ABCDataSource,
    location: VisualLocation,
    link: ContextualLinkEntryConfig,
    context: VisualContext,
    configured: Mapping[FilterName, Sequence[str]],
    *,
    joined: bool,
    drilled_from: DrillUpButton | None,
    carries_site: bool,
) -> CellDrilldown:
    carriable = set(drilldown_filters(data_source, location.type))
    carried = {
        filter_name: _CarriedFilter(drilldown, keys)
        for filter_name, keys in configured.items()
        if filter_name in carriable
        and (drilldown := row_drilldown(data_source, filter_name)) is not None
    }
    row_filters = [name for name in carried if row_has_columns(data_source, name)]
    # A joined service row has every host and service column.
    joined_filters = [name for name in carried if name not in row_filters] if joined else []
    return CellDrilldown(
        columns=_columns(carried, row_filters),
        joined_columns=_columns(carried, joined_filters),
        url=partial(
            _filter_url,
            location,
            context,
            configured,
            carried,
            show_filter_form=link["show_filter_form"],
            drilled_from=drilled_from,
            carries_site=carries_site,
        ),
        includes_time_range=link["include_time_range"],
    )


def _inherited_drilldown(
    location: VisualLocation,
    target: Visual,
    link: ContextualLinkEntryConfig,
    context: VisualContext,
    object_infos: Sequence[InfoName],
    *,
    joined: bool,
    drilled_from: DrillUpButton | None,
) -> CellDrilldown:
    # A joined column's object is its joined service.
    carried_infos = _taken_infos(target, ("host", "service") if joined else object_infos)
    return CellDrilldown(
        columns=["host_name"] if joined else _object_columns(object_infos),
        joined_columns=["service_description"] if joined else [],
        url=partial(
            _inherited_url,
            location,
            context,
            carried_infos,
            carries_site=_carries_site(target, get_single_info_keys(carried_infos)),
            show_filter_form=link["show_filter_form"],
            drilled_from=drilled_from,
        ),
        includes_time_range=link["include_time_range"],
    )


def _taken_infos(target: Visual, object_infos: Sequence[InfoName]) -> list[InfoName]:
    """The parts of the clicked object that a target of single objects takes, as "Link to" carried
    them: a service would narrow a host's view to that service."""
    if not (single_infos := target["single_infos"]):
        return list(object_infos)
    return [info for info in object_infos if info in single_infos]


def _takes_another_object(data_source: ABCDataSource, target: Visual) -> bool:
    """Whether the target takes an object of the row besides its host and service, such as the
    host group of a row of hosts by group."""
    return any(
        info in data_source.infos
        for info in target["single_infos"]
        if info not in ("host", "service")
    )


def _row_object_filters(
    data_source: ABCDataSource,
    target_type: ContextualLinkTargetType,
    target_infos: Sequence[InfoName],
) -> list[FilterName]:
    """The filters naming the row's own object, such as its host group, that the target takes. A
    target of single objects takes only those."""
    carriable = set(drilldown_filters(data_source, target_type))
    infos = [info for info in data_source.infos if not target_infos or info in target_infos]
    return [
        filter_name
        for filter_name in get_single_info_keys(infos)
        if filter_name in carriable and row_has_columns(data_source, filter_name)
    ]


def _carries_site(target: Visual, filter_names: Sequence[FilterName]) -> bool:
    """Whether the row's site goes along, as "Link to" sent it: a customer row's site names the
    customer."""
    return may_add_site_hint(
        target["name"],
        info_keys=tuple(visual_info_registry.keys()),
        single_info_keys=tuple(target["single_infos"]),
        filter_names=tuple(filter_names),
    )


def _columns(
    carried: Mapping[FilterName, _CarriedFilter], filter_names: Sequence[FilterName]
) -> list[ColumnName]:
    return [column for name in filter_names for column in carried[name].drilldown.columns]


def _object_columns(object_infos: Sequence[InfoName]) -> list[ColumnName]:
    return ["host_name", "service_description"] if "service" in object_infos else ["host_name"]


def _object_filters(
    row: Row, object_infos: Sequence[InfoName], *, carries_site: bool
) -> dict[FilterName, FilterHTTPVariables]:
    """The filters naming the row's object, as the Vue object widgets carry them.

    A row of a data source of hosts and services may be about a host alone, with an empty service.
    """
    filters: dict[FilterName, FilterHTTPVariables] = {}
    if carries_site:
        filters["siteopt"] = {"site": str(row["site"])}
    if "host" in object_infos and (host_name := row["host_name"]):
        filters["host"] = {"host": str(host_name)}
    if "service" in object_infos and (service_description := row["service_description"]):
        filters["service"] = {"service": str(service_description)}
    return filters


def _inherited_url(
    location: VisualLocation,
    context: VisualContext,
    object_infos: Sequence[InfoName],
    row: Row,
    *,
    carries_site: bool,
    show_filter_form: bool,
    drilled_from: DrillUpButton | None,
) -> str:
    object_filters = _object_filters(row, object_infos, carries_site=carries_site)
    # The clicked object goes last, so it wins over the same filter in the context.
    return target_url(
        location,
        {**context, **object_filters},
        show_filter_form=show_filter_form,
        drilled_from=drilled_from,
        time_range=None,
    )


def _filter_url(
    location: VisualLocation,
    context: VisualContext,
    configured: Mapping[FilterName, Sequence[str]],
    carried: Mapping[FilterName, _CarriedFilter],
    row: Row,
    *,
    show_filter_form: bool,
    drilled_from: DrillUpButton | None,
    carries_site: bool,
) -> str:
    valued: dict[FilterName, FilterHTTPVariables] = {}
    dropped: list[Dropped] = []
    for filter_name in configured:
        if (carried_filter := carried.get(filter_name)) is None:
            dropped.append(Dropped(filter_name, "not_available"))
            continue
        variables, missing = carried_filter.drilldown.carried([row], carried_filter.keys)
        if variables is not None:
            valued[filter_name] = variables
        if missing:
            dropped.extend(Dropped(filter_name, "no_such_key", key) for key in missing)
        elif variables is None:
            dropped.append(Dropped(filter_name, "no_value"))
    if carries_site and (site := row.get("site")):
        valued["siteopt"] = {"site": str(site)}
    filters = {**context, **valued}
    return target_url(
        location,
        filters,
        show_filter_form=show_filter_form,
        drilled_from=drilled_from,
        time_range=None,
        # A filter the context carries in place of the row's value still travels.
        dropped=[
            entry
            for entry in dropped
            if entry.filter_name in valued or entry.filter_name not in filters
        ],
    )


def target_url(
    location: VisualLocation,
    context: VisualContext,
    *,
    show_filter_form: bool,
    drilled_from: DrillUpButton | None,
    time_range: TimeRangeVariables | None,
    dropped: Sequence[Dropped] = (),
) -> str:
    page, name_variable = _PAGE_BY_TARGET_TYPE[location.type]
    variables: dict[str, str] = {}
    for filter_variables in context.values():
        variables.update(filter_variables)
    if time_range is not None:
        variables["from"] = time_range.from_
        variables["to"] = time_range.to
    # The target's own variables go last, so no filter can override them.
    variables[name_variable] = location.name
    variables["filled_in"] = "filter"
    variables["_show_filter_form"] = "1" if show_filter_form else "0"
    if dropped:
        variables[DROPPED_FILTERS_VAR] = dropped_filters_variable(dropped)
    if drilled_from is not None:
        variables[DRILLED_FROM_VAR] = drilled_from.title
    return makeuri_contextless(request, list(variables.items()), filename=page)
