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
    VisualLinkSpec,
    VisualName,
)

from .type_defs import (
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
    """The stored link that replaces a widget's legacy link to a view or a dashboard. It carries
    the clicked host and the time range and, like "Link to", leaves out the dashboard and widget
    filters."""
    return ContextualLinkInheritedConfig(
        type="inherited",
        location=target,
        include_context=False,
        include_time_range=True,
        show_filter_form=False,
    )
