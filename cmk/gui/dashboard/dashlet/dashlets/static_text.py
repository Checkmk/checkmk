#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.dashboard.dashlet.base import (
    Dashlet,
    RelativeLayoutConstraints,
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
    @override
    def type_name(cls) -> str:
        return "nodata"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Static text")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays a static text to the user.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 100

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(initial_size=WidgetSize(width=30, height=18))

    @classmethod
    @override
    def responsive_layout_constraints(cls) -> ResponsiveLayoutConstraints:
        return ResponsiveLayoutConstraints().with_minimum_height(1)
