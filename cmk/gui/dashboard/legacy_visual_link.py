#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Sequence

from cmk.gui.log import logger
from cmk.gui.type_defs import (
    ColumnSpec,
    ContextualLinkEntryConfig,
    DashboardEmbeddedViewSpec,
    ViewSpec,
    VisualLinkSpec,
    VisualName,
)
from cmk.gui.visual_link import may_add_site_hint
from cmk.gui.visuals.info import visual_info_registry

from .type_defs import (
    ContextFilterConfig,
    ContextualLinkCustomConfig,
    ContextualLinkInheritedConfig,
    ContextualLinkTargetType,
)


def inherited_column_link(
    *, type_name: ContextualLinkTargetType, name: VisualName
) -> ContextualLinkEntryConfig:
    """A column's drill-down that carries the clicked object and the time range. Like "Link to", it
    leaves out the dashboard and widget filters."""
    return ContextualLinkEntryConfig(
        title=name,
        location=(type_name, name),
        filters=[],
        include_context=False,
        include_time_range=True,
        show_filter_form=False,
    )


def painters_with_column_links(painters: Sequence[ColumnSpec]) -> list[ColumnSpec]:
    """Replace each legacy link by a drill-down, which a legacy link left in place would win
    over."""
    return [_with_column_link(painter) for painter in painters]


def embedded_view_with_column_links(
    embedded_view: DashboardEmbeddedViewSpec,
) -> DashboardEmbeddedViewSpec:
    return {**embedded_view, "painters": painters_with_column_links(embedded_view["painters"])}


def _with_column_link(painter: ColumnSpec) -> ColumnSpec:
    if (link_spec := painter.link_spec) is None:
        return painter
    return dataclasses.replace(
        painter,
        link_spec=None,
        column_link=_drilldown(painter.name, link_spec),
    )


def _drilldown(column: str, link_spec: VisualLinkSpec) -> ContextualLinkEntryConfig | None:
    match link_spec.type_name:
        case "views" | "dashboards" as type_name:
            return inherited_column_link(type_name=type_name, name=link_spec.name)
        case _:
            logger.warning(
                "Dropped the link of column %(column)r to %(type_name)s %(name)r: a drill-down"
                " leads only to views and dashboards",
                {"column": column, "type_name": link_spec.type_name, "name": link_spec.name},
            )
            return None


def contextual_link_from_legacy_target(
    target: tuple[ContextualLinkTargetType, VisualName],
) -> ContextualLinkInheritedConfig:
    """The stored link that replaces a widget's legacy link to a view or a dashboard whose single
    objects are not known, carrying the clicked host's site and name."""
    return ContextualLinkInheritedConfig(
        type="inherited",
        location=target,
        include_context=False,
        include_time_range=False,
        show_filter_form=False,
    )


def contextual_link_from_legacy_view(view: ViewSpec) -> ContextualLinkCustomConfig:
    """The stored link that replaces a widget's legacy link to a view, carrying from the clicked
    host what the legacy link carried: its name only for a view of single hosts, and its site
    where that link added it as a hint."""
    host_filters = ["host"] if "host" in view["single_infos"] else []
    site_filters = (
        ["siteopt"]
        if may_add_site_hint(
            view["name"],
            info_keys=tuple(visual_info_registry.keys()),
            single_info_keys=tuple(view["single_infos"]),
            filter_names=tuple(host_filters),
        )
        else []
    )
    return ContextualLinkCustomConfig(
        type="custom",
        links=[
            ContextualLinkEntryConfig(
                title=str(view["title"]),
                location=("views", view["name"]),
                filters=[
                    ContextFilterConfig(filter_id=filter_id)
                    for filter_id in site_filters + host_filters
                ],
                include_context=False,
                include_time_range=False,
                show_filter_form=False,
            )
        ],
    )
