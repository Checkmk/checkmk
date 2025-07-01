#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.gui.config import Config
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.sidebar import footnotelinks, PageHandlers, SidebarSnapin


class NagVisMaps(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "nagvis_maps"

    @classmethod
    def title(cls) -> str:
        return _("NagVis maps")

    @classmethod
    def description(cls) -> str:
        return _("List of available NagVis maps")

    @classmethod
    def refresh_regularly(cls) -> bool:
        return False

    def show(self, config: Config) -> None:
        html.div(_("Loading maps..."), class_="loading")
        html.javascript("cmk.sidebar.fetch_nagvis_snapin_contents()")

    def page_handlers(self) -> PageHandlers:
        return {
            "ajax_nagvis_maps_snapin": self._ajax_show_nagvis_maps_snapin,
        }

    def _ajax_show_nagvis_maps_snapin(self, config: Config) -> None:
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

    def _show_table(self, api_request: Mapping[str, Any]) -> None:
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
                ]
                + self._sub_state_class(map_cfg)
                + self._stale_class(map_cfg),
                title=self._state_title(map_cfg),
            )
            html.a(map_cfg["alias"], href=map_cfg["url"], class_="link", target="main")
            html.close_td()
            html.close_tr()

        html.close_tbody()
        html.close_table()

    def _state_class(self, map_cfg: Mapping[str, Any]) -> str:
        return {
            "OK": "state0",
            "UP": "state0",
            "WARNING": "state1",
            "CRITICAL": "state2",
            "DOWN": "state2",
            "UNREACHABLE": "state2",
            "PENDING": "statep",
        }.get(map_cfg["summary_state"], "state3")

    def _sub_state_class(self, map_cfg: Mapping[str, Any]) -> list[str]:
        if map_cfg["summary_in_downtime"]:
            return ["stated"]
        if map_cfg["summary_problem_has_been_acknowledged"]:
            return ["statea"]
        return []

    def _stale_class(self, map_cfg: Mapping[str, Any]) -> list[str]:
        if map_cfg["summary_stale"]:
            return ["stale"]
        return []

    def _state_title(self, map_cfg: Mapping[str, Any]) -> str:
        title = map_cfg["summary_state"]

        if map_cfg["summary_in_downtime"]:
            title += " (Downtime)"
        if map_cfg["summary_problem_has_been_acknowledged"]:
            title += " (Acknowledged)"

        if map_cfg["summary_stale"]:
            title += " (Stale)"

        if "summary_output" in map_cfg:
            # Added in NagVis 1.9.35 (with Checkmk 2.2.0b8)
            title += f" - {map_cfg['summary_output']}"

        return title

    def _show_footnote_links(self) -> None:
        edit_url = "../nagvis/"
        footnotelinks([(_("Edit"), edit_url)])

    def _show_tree(self, api_request: Mapping[str, Any]) -> None:
        html.open_ul()
        self._show_tree_nodes(api_request["maps"]["maps"], api_request["maps"]["childs"])
        html.close_ul()

    def _show_tree_nodes(
        self,
        maps: Mapping[str, Mapping[str, Any]],
        children: Mapping[str, Mapping[str, Mapping[str, Any]]],
    ) -> None:
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
                ):
                    self._show_tree_nodes(children[map_name], children)
            else:
                html.a(map_cfg["alias"], href=map_cfg["url"], target="main", class_="link")
            html.close_li()
