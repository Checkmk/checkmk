#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.dashboard.dashlet.base import (
    Dashlet,
    RelativeLayoutConstraints,
    ResponsiveLayoutBreakpointConstraints,
    ResponsiveLayoutConstraints,
    WidgetSize,
)
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.i18n import _


class StaticTextDashletConfig(DashletConfig):
    text: str


class StaticTextDashlet(Dashlet[StaticTextDashletConfig]):
    """Dashlet that displays a static text"""

    @classmethod
    def type_name(cls) -> str:
        return "nodata"

    @classmethod
    def title(cls) -> str:
        return _("Static text")

    @classmethod
    def description(cls) -> str:
        return _("Displays a static text to the user.")

    @classmethod
    def sort_index(cls) -> int:
        return 100

    @classmethod
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(initial_size=WidgetSize(width=30, height=18))

    @classmethod
    def responsive_layout_constraints(cls) -> ResponsiveLayoutConstraints:
        # same as default, but allow minimum height of 1 for all breakpoints
        default = ResponsiveLayoutConstraints()
        return ResponsiveLayoutConstraints(
            XS=ResponsiveLayoutBreakpointConstraints(
                initial_size=default.XS.initial_size,
                minimum_size=WidgetSize(width=default.XS.minimum_size.width, height=1),
            ),
            S=ResponsiveLayoutBreakpointConstraints(
                initial_size=default.S.initial_size,
                minimum_size=WidgetSize(width=default.S.minimum_size.width, height=1),
            ),
            M=ResponsiveLayoutBreakpointConstraints(
                initial_size=default.M.initial_size,
                minimum_size=WidgetSize(width=default.M.minimum_size.width, height=1),
            ),
            L=ResponsiveLayoutBreakpointConstraints(
                initial_size=default.L.initial_size,
                minimum_size=WidgetSize(width=default.L.minimum_size.width, height=1),
            ),
            XL=ResponsiveLayoutBreakpointConstraints(
                initial_size=default.XL.initial_size,
                minimum_size=WidgetSize(width=default.XL.minimum_size.width, height=1),
            ),
        )
