#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _

from ._base import SidebarSnapin


class CurrentTime(SidebarSnapin):
    @staticmethod
    def type_name():
        return "time"

    @classmethod
    def title(cls):
        return _("Server time")

    @classmethod
    def description(cls):
        return _("A large clock showing the current time of the web server")

    @classmethod
    def refresh_regularly(cls):
        return True

    def show(self, config: Config) -> None:
        html.div(time.strftime("%H:%M"), class_="time")
