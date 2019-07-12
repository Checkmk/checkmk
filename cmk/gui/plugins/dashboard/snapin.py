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
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import DropdownChoice

from cmk.gui.plugins.dashboard import (
    IFrameDashlet,
    dashlet_registry,
)


@dashlet_registry.register
class SnapinDashlet(IFrameDashlet):
    """Dashlet that displays a sidebar snapin"""
    @classmethod
    def type_name(cls):
        return "snapin"

    @classmethod
    def title(cls):
        return _("Sidebar Snapin")

    @classmethod
    def description(cls):
        return _("Displays a sidebar snapin.")

    @classmethod
    def sort_index(cls):
        return 55

    @classmethod
    def initial_size(cls):
        return (27, 20)

    @classmethod
    def initial_refresh_interval(cls):
        return 30

    @classmethod
    def vs_parameters(cls):
        return [
            ("snapin",
             DropdownChoice(
                 title=_("Snapin"),
                 help=_("Choose the snapin you would like to show."),
                 choices=cls._snapin_choices,
             )),
        ]

    @classmethod
    def _snapin_choices(cls):
        import cmk.gui.sidebar as sidebar
        return sorted([(k, v.title()) for k, v in sidebar.snapin_registry.items()],
                      key=lambda x: x[1])

    def display_title(self):
        import cmk.gui.sidebar as sidebar
        return sidebar.snapin_registry[self._dashlet_spec["snapin"]].title()

    def update(self):
        import cmk.gui.sidebar as sidebar
        dashlet = self._dashlet_spec
        snapin = sidebar.snapin_registry.get(self._dashlet_spec['snapin'])
        if not snapin:
            raise MKUserError(None, _('The configured snapin does not exist.'))
        snapin_instance = snapin()

        html.set_browser_reload(self.refresh_interval())
        html.html_head(_('Snapin Dashlet'))
        html.open_body(class_="side")
        html.open_div(id_="check_mk_sidebar")
        html.open_div(id_="side_content")
        html.open_div(id_="snapin_container_%s" % dashlet['snapin'], class_="snapin")
        html.open_div(id_="snapin_%s" % dashlet['snapin'], class_="content")
        styles = snapin_instance.styles()
        if styles:
            html.style(styles)
        snapin_instance.show()
        html.close_div()
        html.close_div()
        html.close_div()
        html.close_div()
        html.body_end()
