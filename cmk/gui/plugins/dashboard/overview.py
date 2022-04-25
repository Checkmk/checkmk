#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.htmllib.context import html
from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard.utils import Dashlet, dashlet_registry
from cmk.gui.utils.theme import theme


@dashlet_registry.register
class OverviewDashlet(Dashlet):
    """Dashlet that displays an introduction and Check_MK logo"""

    @classmethod
    def type_name(cls):
        return "overview"

    @classmethod
    def title(cls):
        return _("Overview / Introduction")

    @classmethod
    def description(cls):
        return _("Displays an introduction and Checkmk logo.")

    @classmethod
    def sort_index(cls):
        return 0

    @classmethod
    def is_selectable(cls):
        return False  # can not be selected using the dashboard editor

    def show(self):
        html.open_table(class_="dashlet_overview")
        html.open_tr()
        html.open_td(valign="top")
        html.open_a(href="https://checkmk.com/")
        html.img(theme.url("images/check_mk.trans.120.png"), style="margin-right: 30px;")
        html.close_a()
        html.close_td()

        html.open_td()
        html.h2("CheckMK")
        html.write_text(
            _(
                "Welcome to Checkmk. If you want to learn more about Checkmk, please visit "
                'our <a href="https://checkmk.com/" target="_blank">user manual</a>.'
            )
        )
        html.close_td()

        html.close_tr()
        html.close_table()
