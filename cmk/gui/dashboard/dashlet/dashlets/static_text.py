#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.dashboard.dashlet.base import Dashlet, RelativeLayoutConstraints, WidgetSize
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
