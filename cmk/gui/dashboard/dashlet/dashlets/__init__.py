#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..registry import DashletRegistry
from .static_text import StaticTextDashlet, StaticTextDashletConfig
from .view import copy_view_into_dashlet, LinkedViewDashletConfig, ViewDashletConfig

__all__ = [
    "register_dashlets",
    "StaticTextDashletConfig",
    "StaticTextDashlet",
    "ViewDashletConfig",
    "LinkedViewDashletConfig",
    "copy_view_into_dashlet",
]


def register_dashlets(dashlet_registry: DashletRegistry) -> None:
    dashlet_registry.register(StaticTextDashlet)
