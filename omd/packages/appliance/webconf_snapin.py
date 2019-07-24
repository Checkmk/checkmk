#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
)


@snapin_registry.register
class SidebarSnapinCMAWebconf(SidebarSnapin):
    @staticmethod
    def type_name():
        return "webconf"

    @classmethod
    def title(cls):
        return _("Check_MK Appliance")

    @classmethod
    def description(cls):
        return _("Access to the Check_MK Appliance Web Configuration")

    @classmethod
    def allowed_roles(cls):
        return ["admin"]

    def show(self):

        import imp
        try:
            cma_nav = imp.load_source("cma_nav", "/usr/lib/python2.7/cma_nav.py")
        except IOError:
            html.show_error(_("Unable to import cma_nav module"))
            return

        base_url = "/webconf/"

        self._iconlink(_("Main Menu"), base_url, "home")

        for url, icon, title, _descr in cma_nav.modules():
            url = base_url + url
            self._iconlink(title, url, icon)

    # Our version of iconlink -> the images are located elsewhere
    def _iconlink(self, text, url, icon):
        html.open_a(class_=["iconlink", "link"], target="main", href=url)
        html.icon(icon="/webconf/images/icon_%s.png" % icon, title=None, cssclass="inline")
        html.write(text)
        html.close_a()
        html.br()
