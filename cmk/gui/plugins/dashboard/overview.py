#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.dashboard import (
    Dashlet,
    dashlet_registry,
)


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
        return _("Displays an introduction and Check_MK logo.")

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
        html.img(html.theme_url("images/check_mk.trans.120.png"), style="margin-right: 30px;")
        html.close_a()
        html.close_td()

        html.open_td()
        html.h2("CheckMK")
        html.write_html('Welcome to CheckMK. If you want to learn more about CheckMK, please visit '
                        'our <a href="https://checkmk.com/" target="_blank">user manual</a>.')
        html.close_td()

        html.close_tr()
        html.close_table()
