#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from cmk.ccc.plugin_registry import Registry

from cmk.gui.config import Config

from .type_defs import DashboardConfig, DashboardName

# Declare constants to be used in the definitions of the dashboards
GROW = 0
MAX = -1

builtin_dashboards: dict[DashboardName, DashboardConfig] = {}


@dataclass(frozen=True)
class BuiltinDashboardExtender:
    ident: str
    callable: Callable[
        [Mapping[DashboardName, DashboardConfig], Config], dict[DashboardName, DashboardConfig]
    ]


class BuiltinDashboardExtenderRegistry(Registry[BuiltinDashboardExtender]):
    def plugin_name(self, instance: BuiltinDashboardExtender) -> str:
        return instance.ident


def noop_builtin_dashboard_extender(
    dashboards: Mapping[DashboardName, DashboardConfig], config: Config
) -> dict[DashboardName, DashboardConfig]:
    return {**dashboards}


builtin_dashboard_extender_registry = BuiltinDashboardExtenderRegistry()
