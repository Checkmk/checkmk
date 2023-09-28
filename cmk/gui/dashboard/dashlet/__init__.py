#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.dashboard.type_defs import (
    DashletConfig,
    DashletId,
    DashletPosition,
    DashletRefreshAction,
    DashletRefreshInterval,
    DashletSize,
)

from .base import Dashlet, IFrameDashlet
from .dashlets import (
    copy_view_into_dashlet,
    LinkedViewDashletConfig,
    register_dashlets,
    StaticTextDashlet,
    StaticTextDashletConfig,
    StatsDashletConfig,
    ViewDashletConfig,
)
from .figure_dashlet import ABCFigureDashlet, FigureDashletPage
from .registry import dashlet_registry, DashletRegistry

__all__ = [
    "DashletId",
    "DashletRefreshInterval",
    "DashletRefreshAction",
    "DashletSize",
    "DashletPosition",
    "register_dashlets",
    "StaticTextDashletConfig",
    "StaticTextDashlet",
    "DashletRegistry",
    "dashlet_registry",
    "Dashlet",
    "IFrameDashlet",
    "DashletConfig",
    "ViewDashletConfig",
    "StatsDashletConfig",
    "LinkedViewDashletConfig",
    "copy_view_into_dashlet",
    "FigureDashletPage",
    "ABCFigureDashlet",
]
