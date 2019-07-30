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
"""Mode for searching hosts"""

import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.valuespec import TextAscii

from cmk.gui.plugins.wato.utils import mode_registry, configure_attributes
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.context_buttons import global_buttons

from cmk.gui.globals import html
from cmk.gui.i18n import _


@mode_registry.register
class ModeSearch(WatoMode):
    @classmethod
    def name(cls):
        return "search"

    @classmethod
    def permissions(cls):
        return ["hosts"]

    def __init__(self):
        super(ModeSearch, self).__init__()
        self._folder = watolib.Folder.current()

    def title(self):
        return _("Search for hosts below %s") % self._folder.title()

    def buttons(self):
        global_buttons()
        html.context_button(_("Folder"), self._folder.url(), "back")

    def action(self):
        return "folder"

    def page(self):
        self._folder.show_breadcrump()

        # Show search form
        html.begin_form("edit_host", method="GET")
        html.prevent_password_auto_completion()

        basic_attributes = [
            ("host_search_host", TextAscii(title=_("Hostname",)), ""),
        ]
        html.set_focus("host_search_host")

        # Attributes
        configure_attributes(
            new=False,
            hosts={},
            for_what="host_search",
            parent=None,
            varprefix="host_search_",
            basic_attributes=basic_attributes,
        )

        # Button
        forms.end()
        html.button("_local", _("Search in %s") % self._folder.title(), "submit")
        html.hidden_field("host_search", "1")
        html.hidden_fields()
        html.end_form()
