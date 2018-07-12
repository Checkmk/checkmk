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

import cmk

from cmk.gui.i18n import _
from cmk.gui.globals import html
from . import SidebarSnapin, bulletlink

class About(SidebarSnapin):
    @staticmethod
    def type_name():
        return "about"


    def title(self):
        return _("About Check_MK")


    def description(self):
        return _("Version information and Links to Documentation, "
                 "Homepage and Download of Check_MK")


    def show(self):
        html.write(_("Version: ") + cmk.__version__)
        html.open_ul()
        bulletlink(_("Homepage"),        "https://mathias-kettner.com/check_mk.html")
        bulletlink(_("Documentation"),   "https://mathias-kettner.com/checkmk.html")
        bulletlink(_("Download"),        "https://mathias-kettner.com/check_mk_download.html")
        bulletlink("Mathias Kettner",    "https://mathias-kettner.com")
        html.close_ul()

    def allowed_roles(self):
        return [ "admin", "user", "guest" ]
