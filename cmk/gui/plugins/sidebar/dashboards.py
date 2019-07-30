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

import cmk.gui.config as config
import cmk.gui.dashboard as dashboard
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    visuals_by_topic,
    bulletlink,
    footnotelinks,
)


@snapin_registry.register
class Dashboards(SidebarSnapin):
    @staticmethod
    def type_name():
        return "dashboards"

    @classmethod
    def title(cls):
        return _("Dashboards")

    @classmethod
    def description(cls):
        return _("Links to all dashboards")

    def show(self):
        dashboard.load_dashboards()

        def render_topic(topic, s, foldable=True):
            first = True
            for t, title, name, _is_view in s:
                if t == topic:
                    if first:
                        if foldable:
                            html.begin_foldable_container("dashboards",
                                                          topic,
                                                          False,
                                                          topic,
                                                          indent=True)
                        else:
                            html.open_ul()
                        first = False
                    bulletlink(title,
                               'dashboard.py?name=%s' % name,
                               onclick="return cmk.sidebar.wato_views_clicked(this)")

            if not first:  # at least one item rendered
                if foldable:
                    html.end_foldable_container()
                else:
                    html.open_ul()

        by_topic = visuals_by_topic(dashboard.permitted_dashboards().items(),
                                    default_order=[_('Overview')])
        topics = [topic for topic, _entry in by_topic]

        if len(topics) < 2:
            render_topic(by_topic[0][0], by_topic[0][1], foldable=False)
        else:
            for topic, s in by_topic:
                render_topic(topic, s)

        links = []
        if config.user.may("general.edit_dashboards"):
            if config.debug:
                links.append((_("Export"), "export_dashboards.py"))
            links.append((_("Edit"), "edit_dashboards.py"))
            footnotelinks(links)
