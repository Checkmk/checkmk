#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.dashboard.dashlet.base import Dashlet
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.i18n import _


class FailedNotificationsDashletConfig(DashletConfig): ...


class FailedNotificationsDashlet(Dashlet[FailedNotificationsDashletConfig]):
    """Dashlet notifying users in case of failure to send notifications"""

    @classmethod
    @override
    def type_name(cls) -> str:
        return "notify_failed_notifications"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Failed notifications")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Display GUI notifications in case notification mechanism fails")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 0

    @classmethod
    @override
    def is_selectable(cls) -> bool:
        return False
