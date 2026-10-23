#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import override

from cmk.gui.dashboard.type_defs import StatsDashletConfig
from cmk.gui.i18n import _
from cmk.gui.type_defs import SingleInfos

from ..base import RelativeLayoutConstraints, WidgetSize
from ..figure_dashlet import ABCFigureDashlet


class HostStatsDashlet(ABCFigureDashlet[StatsDashletConfig]):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "hoststats"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Host statistics")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays statistics about host states as a hexagon and a table.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 45

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(
            initial_size=WidgetSize(width=30, height=18), is_resizable=False
        )

    @override
    def infos(self) -> SingleInfos:
        return ["host"]


class ServiceStatsDashlet(ABCFigureDashlet[StatsDashletConfig]):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "servicestats"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Service statistics")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays statistics about service states as a hexagon and a table.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 50

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(
            initial_size=WidgetSize(width=30, height=18), is_resizable=False
        )


class EventStatsDashlet(ABCFigureDashlet[StatsDashletConfig]):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "eventstats"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Event statistics")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays statistics about events as a hexagon and a table.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 55

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(
            initial_size=WidgetSize(width=30, height=18), is_resizable=False
        )

    @override
    def infos(self) -> SingleInfos:
        return ["host", "event"]
