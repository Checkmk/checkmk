#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.dashboard.dashlet.base import IFrameDashlet, RelativeLayoutConstraints, WidgetSize
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.i18n import _


class URLDashletConfig(DashletConfig):
    url: str


class URLDashlet(IFrameDashlet[URLDashletConfig]):
    """Dashlet that displays a custom webpage"""

    @classmethod
    @override
    def type_name(cls) -> str:
        return "url"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Custom URL")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays the content of a custom website.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 80

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(initial_size=WidgetSize(width=30, height=10))
