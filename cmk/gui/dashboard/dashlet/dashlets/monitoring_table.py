#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.dashboard.dashlet.base import Dashlet, ResponsiveLayoutConstraints
from cmk.gui.dashboard.monitoring_tables import MONITORING_TABLES
from cmk.gui.dashboard.type_defs import MonitoringTableDashletConfig
from cmk.gui.i18n import _
from cmk.gui.type_defs import SingleInfos


class MonitoringTableDashlet(Dashlet[MonitoringTableDashletConfig]):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "monitoring_table"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Monitoring table")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays a monitoring table, such as the one of the All hosts page.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 11

    @classmethod
    @override
    def has_context(cls) -> bool:
        return True

    @classmethod
    @override
    def responsive_layout_constraints(cls) -> ResponsiveLayoutConstraints:
        return ResponsiveLayoutConstraints.large_default()

    @override
    def infos(self) -> SingleInfos:
        return list(MONITORING_TABLES[self._dashlet_spec["table"]].infos)
