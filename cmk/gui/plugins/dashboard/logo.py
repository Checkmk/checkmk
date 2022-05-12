#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard.utils import Dashlet, dashlet_registry
from cmk.gui.utils.theme import theme


@dashlet_registry.register
class MKLogoDashlet(Dashlet):
    """Dashlet that displays the Check_MK logo"""

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
    def sort_index(cls):
        return 0

    @classmethod
    def is_selectable(cls):
        return False  # can not be selected using the dashboard editor

    def show(self):
        html.open_a(href="https://checkmk.com/", target="_blank")
        html.img(theme.url("images/check_mk.trans.120.png"), style="margin-right: 30px;")
        html.close_a()
