#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.dashboard.dashlet.base import Dashlet
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.i18n import _
from cmk.gui.user_message import render_user_message_table


class MessageUsersDashletConfig(DashletConfig): ...


class MessageUsersDashlet(Dashlet[MessageUsersDashletConfig]):
    """Dashlet that displays GUI messages for users"""

    @classmethod
    def type_name(cls):
        return "user_messages"

    @classmethod
    def title(cls):
        return _("User messages")

    @classmethod
    def description(cls):
        return _("Display GUI messages sent to users.")

    @classmethod
    def sort_index(cls) -> int:
        return 75

    def show(self):
        render_user_message_table("dashlet")
