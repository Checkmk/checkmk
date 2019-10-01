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

from cmk.gui.globals import html
from cmk.gui.i18n import _

from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    footnotelinks,
)


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
        return _("List of available NagVis maps")

    @classmethod
    def allowed_roles(cls):
        return ["admin", "user", "guest"]

    @classmethod
    def refresh_regularly(cls):
        return True

    def show(self):
        html.javascript("cmk.sidebar.fetch_nagvis_snapin_contents()")

    def page_handlers(self):
        return {
            "ajax_nagvis_maps_snapin": self._ajax_show_nagvis_maps_snapin,
        }

    def _ajax_show_nagvis_maps_snapin(self):
        request = html.get_request()
        if request["type"] == "table":
            self._show_table(request)
        elif request["type"] == "tree":
            self._show_tree(request)
        elif request["type"] == "error":
            html.show_error(request["message"])
        else:
            raise NotImplementedError()

        self._show_footnote_links()

    def _show_table(self, request):
        html.open_table(class_="allhosts")
        html.open_tbody()

        for map_cfg in request["maps"]:
            html.open_tr()
            html.open_td()
            html.div("",
                     class_=[
                         "statebullet",
                         self._state_class(map_cfg),
                         self._sub_state_class(map_cfg),
                         self._stale_class(map_cfg)
                     ],
                     title=self._state_title(map_cfg))
            html.a(map_cfg["alias"], href=map_cfg["url"], class_="link", target="main")
            html.close_td()
            html.close_tr()

        html.close_tbody()
        html.close_table()

    def _state_class(self, map_cfg):
        return {
            "OK": "state0",
            "UP": "state0",
            "WARNING": "state1",
            "CRITICAL": "state2",
            "DOWN": "state2",
            "UNREACHABLE": "state2",
        }.get(map_cfg["summary_state"], "state3")

    def _sub_state_class(self, map_cfg):
        if map_cfg["summary_in_downtime"]:
            return "stated"
        elif map_cfg["summary_problem_has_been_acknowledged"]:
            return "statea"

    def _stale_class(self, map_cfg):
        if map_cfg["summary_stale"]:
            return "stale"

    def _state_title(self, map_cfg):
        title = map_cfg["summary_state"]

        if map_cfg["summary_in_downtime"]:
            title += " (Downtime)"
        if map_cfg["summary_problem_has_been_acknowledged"]:
            title += " (Acknowledged)"

        if map_cfg["summary_stale"]:
            title += " (Stale)"

        return title

    def _show_footnote_links(self):
        edit_url = "../nagvis/"
        footnotelinks([(_("Edit"), edit_url)])

    def _show_tree(self, request):
        self._show_tree_nodes(request["maps"]["maps"], request["maps"]["childs"])

    def _show_tree_nodes(self, maps, children):
        for map_name, map_cfg in maps.iteritems():
            html.open_li()
            if map_name in children:
                html.begin_foldable_container(treename="nagvis",
                                              id_=map_name,
                                              isopen=False,
                                              title=map_cfg["alias"],
                                              title_url=map_cfg["url"],
                                              title_target="main",
                                              indent=False)
                self._show_tree_nodes(children[map_name], children)
                html.end_foldable_container()
            else:
                html.a(map_cfg["alias"], href=map_cfg["url"], target="main", class_="link")
            html.close_li()
