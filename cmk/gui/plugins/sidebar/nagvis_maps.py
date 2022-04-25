#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.htmllib.context import html
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import footnotelinks, SidebarSnapin, snapin_registry


@snapin_registry.register
class NagVisMaps(SidebarSnapin):
    @staticmethod
    def type_name():
        return "nagvis_maps"

    @classmethod
    def title(cls):
        return _("NagVis maps")

    @classmethod
    def description(cls):
        return _("List of available NagVis maps")

    @classmethod
    def allowed_roles(cls):
        return ["admin", "user", "guest"]

    @classmethod
    def refresh_regularly(cls):
        return False

    def show(self):
        html.div(_("Loading maps..."), class_="loading")
        html.javascript("cmk.sidebar.fetch_nagvis_snapin_contents()")

    def page_handlers(self):
        return {
            "ajax_nagvis_maps_snapin": self._ajax_show_nagvis_maps_snapin,
        }

    def _ajax_show_nagvis_maps_snapin(self):
        api_request = request.get_request()
        if api_request["type"] == "table":
            self._show_table(api_request)
        elif api_request["type"] == "tree":
            self._show_tree(api_request)
        elif api_request["type"] == "error":
            html.show_error(api_request["message"])
        else:
            raise NotImplementedError()

        self._show_footnote_links()

    def _show_table(self, api_request):
        html.open_table(class_="allhosts")
        html.open_tbody()

        for map_cfg in api_request["maps"]:
            html.open_tr()
            html.open_td()
            html.div(
                "",
                class_=[
                    "statebullet",
                    self._state_class(map_cfg),
                    self._sub_state_class(map_cfg),
                    self._stale_class(map_cfg),
                ],
                title=self._state_title(map_cfg),
            )
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
        if map_cfg["summary_problem_has_been_acknowledged"]:
            return "statea"
        return None

    def _stale_class(self, map_cfg):
        if map_cfg["summary_stale"]:
            return "stale"
        return None

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

    def _show_tree(self, api_request):
        html.open_ul()
        self._show_tree_nodes(api_request["maps"]["maps"], api_request["maps"]["childs"])
        html.close_ul()

    def _show_tree_nodes(self, maps, children):
        for map_name, map_cfg in maps.items():
            html.open_li()
            if map_name in children:
                with foldable_container(
                    treename="nagvis",
                    id_=map_name,
                    isopen=False,
                    title=map_cfg["alias"],
                    title_url=map_cfg["url"],
                    title_target="main",
                    indent=False,
                    icon="foldable_sidebar",
                ):
                    self._show_tree_nodes(children[map_name], children)
            else:
                html.a(map_cfg["alias"], href=map_cfg["url"], target="main", class_="link")
            html.close_li()
