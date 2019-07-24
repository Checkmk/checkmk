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
from cmk.gui.valuespec import TextUnicode

from cmk.gui.plugins.dashboard import (
    Dashlet,
    dashlet_registry,
)


@dashlet_registry.register
class StaticTextDashlet(Dashlet):
    """Dashlet that displays a static text"""
    @classmethod
    def type_name(cls):
        return "nodata"

    @classmethod
    def title(cls):
        return _("Static text")

    @classmethod
    def description(cls):
        return _("Displays a static text to the user.")

    @classmethod
    def sort_index(cls):
        return 100

    @classmethod
    def vs_parameters(cls):
        return [
            ("text", TextUnicode(
                title=_('Text'),
                size=50,
            )),
        ]

    def show(self):
        html.open_div(class_="nodata")
        html.open_div(class_="msg")
        html.write(self._dashlet_spec.get("text", ""))
        html.close_div()
        html.close_div()

    @classmethod
    def styles(cls):
        return """
div.dashlet_inner div.nodata {
    width: 100%;
    height: 100%;
}

div.dashlet_inner.background div.nodata div.msg {
    color: #000;
}

div.dashlet_inner div.nodata div.msg {
    padding: 10px;
}

}"""
