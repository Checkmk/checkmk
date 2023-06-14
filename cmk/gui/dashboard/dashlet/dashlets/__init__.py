#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..registry import DashletRegistry
from .custom_url import URLDashlet
from .failed_notifications import FailedNotificationsDashlet
from .graph import TemplateGraphDashlet
from .logo import MKLogoDashlet
from .snapin import SnapinDashlet
from .static_text import StaticTextDashlet, StaticTextDashletConfig
from .stats import EventStatsDashlet, HostStatsDashlet, ServiceStatsDashlet, StatsDashletConfig
from .user_messages import MessageUsersDashlet
from .view import (
    copy_view_into_dashlet,
    LinkedViewDashlet,
    LinkedViewDashletConfig,
    ViewDashlet,
    ViewDashletConfig,
)

__all__ = [
    "register_dashlets",
    "StaticTextDashletConfig",
    "StaticTextDashlet",
    "ViewDashletConfig",
    "StatsDashletConfig",
    "LinkedViewDashletConfig",
    "copy_view_into_dashlet",
]


def register_dashlets(dashlet_registry: DashletRegistry) -> None:
    dashlet_registry.register(StaticTextDashlet)
    dashlet_registry.register(URLDashlet)
    dashlet_registry.register(FailedNotificationsDashlet)
    dashlet_registry.register(TemplateGraphDashlet)
    dashlet_registry.register(MKLogoDashlet)
    dashlet_registry.register(SnapinDashlet)
    dashlet_registry.register(HostStatsDashlet)
    dashlet_registry.register(ServiceStatsDashlet)
    dashlet_registry.register(EventStatsDashlet)
    dashlet_registry.register(MessageUsersDashlet)
    dashlet_registry.register(ViewDashlet)
    dashlet_registry.register(LinkedViewDashlet)
