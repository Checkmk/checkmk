#!/usr/bin/python
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

import time

from cmk.gui.i18n import _
from cmk.gui.globals import html
from . import SidebarSnapin, snapin_registry
from cmk.gui.plugins.sidebar import snapin_width

@snapin_registry.register
class CurrentTime(SidebarSnapin):
    @staticmethod
    def type_name():
        return "time"

    @classmethod
    def title(cls):
        return _("Server Time")

    @classmethod
    def description(cls):
        return _("A large clock showing the current time of "
                 "the web server")

    def show(self):
        html.div(time.strftime("%H:%M"), class_="time")

    def styles(self):
        return """
div.time {
   text-align: center;
   font-size: 18pt;
   font-weight: bold;
   /* The border needs to be substracted from the width */
   border: 1px solid #8cc;
   -moz-border-radius: 10px;
   background-color: #588;
   color: #aff;
   width: %dpx;
}
""" % (snapin_width - 2)
