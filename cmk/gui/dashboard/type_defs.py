#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, TypedDict

from cmk.gui.type_defs import FilterName, GraphRenderOptionsVS, SingleInfos, Visual, VisualContext
from cmk.gui.valuespec import TimerangeValue

DashboardName = str
DashletId = int
DashletRefreshInterval = bool | int
DashletRefreshAction = str | None
DashletSize = tuple[int, int]
DashletPosition = tuple[int, int]


class _DashletConfigMandatory(TypedDict):
    type: str


class DashletConfig(_DashletConfigMandatory, total=False):
    single_infos: SingleInfos
    title: str
    title_url: str
    context: VisualContext
    # TODO: Could not a place which sets this flag. Can we remove it?
    reload_on_resize: bool
    position: DashletPosition
    size: DashletSize
    background: bool
    show_title: bool | Literal["transparent"]


class ABCGraphDashletConfig(DashletConfig):
    timerange: TimerangeValue
    graph_render_options: GraphRenderOptionsVS


class DashboardConfig(Visual):
    mtime: int
    dashlets: list[DashletConfig]
    show_title: bool
    mandatory_context_filters: list[FilterName]
