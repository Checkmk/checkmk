#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.dashboard.dashlet.base import Dashlet
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.theme.current_theme import theme


class MKLogoDashletConfig(DashletConfig): ...


class MKLogoDashlet(Dashlet[MKLogoDashletConfig]):
    """Dashlet that displays the Checkmk logo"""

    @classmethod
    def type_name(cls):
        return "mk_logo"

    @classmethod
    def title(cls):
        return _("Checkmk Logo")

    @classmethod
    def description(cls):
        return _("Shows the Checkmk logo.")

    @classmethod
    def sort_index(cls) -> int:
        return 0

    @classmethod
    def is_selectable(cls) -> bool:
        return False  # can not be selected using the dashboard editor

    def show(self):
        html.open_a(href="https://checkmk.com/", target="_blank")
        html.img(theme.url("images/check_mk.trans.120.png"), style="margin-right: 30px;")
        html.close_a()
