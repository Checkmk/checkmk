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

import cmk.gui.config as config
from cmk.gui.i18n import _

from . import SidebarSnapin, snapin_registry

@snapin_registry.register
class NagVisMaps(SidebarSnapin):
    @staticmethod
    def type_name():
        return "nagvis_maps"


    @classmethod
    def title(cls):
        return _("NagVis Maps")


    @classmethod
    def description(cls):
        return _("List of available NagVis maps. This only works with NagVis 1.5 and above. ")


    def show(self):
        return "%snagvis/server/core/ajax_handler.php?mod=Multisite&act=getMaps" % (config.url_prefix())


    @classmethod
    def allowed_roles(cls):
        return [ "admin", "user", "guest" ]


    def styles(self):
        return """
div.state1.statea {
    border-color: #ff0;
}
div.state2.statea {
    border-color: #f00;
}
div.statea {
    background-color: #0b3;
}
div.state1.stated {
    border-color: #ff0;
}
div.state2.stated {
    border-color: #f00;
}
div.stated {
    background-color: #0b3;
}
"""

    @classmethod
    def refresh_regularly(cls):
        return True
