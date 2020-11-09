#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Tuple, Any
import cmk.gui.bi as bi
from cmk.gui.i18n import _
from cmk.gui.globals import html, request
from cmk.gui.htmllib import HTML

from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    bulletlink,
)

from cmk.gui.utils.urls import makeuri_contextless


@snapin_registry.register
class SidebarSnapinAggregationGroupList(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "biaggr_groups"

    @classmethod
    def title(cls) -> str:
        return _("BI Aggregation Groups")

    @classmethod
    def description(cls) -> str:
        return _("A direct link to all groups of BI aggregations")

    def show(self) -> None:
        html.open_ul()
        for group in bi.get_aggregation_group_trees():
            bulletlink(group, "view.py?view_name=aggr_group&aggr_group=%s" % html.urlencode(group))
        html.close_ul()


@snapin_registry.register
class SidebarSnapinAggregationGroupTree(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "biaggr_groups_tree"

    @classmethod
    def title(cls) -> str:
        return _("BI Aggregation Groups Tree")

    @classmethod
    def description(cls) -> str:
        return _("A direct link to all groups of BI aggregations organized as tree")

    def show(self) -> None:
        tree: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        for group in bi.get_aggregation_group_trees():
            self._build_tree(group.split("/"), tree, tuple())
        self._render_tree(tree)

    def _build_tree(self, group, parent, path):
        this_node = group[0]
        path = path + (this_node,)
        child = parent.setdefault(this_node, {"__path__": path})
        children = group[1:]
        if children:
            child = child.setdefault('__children__', {})
            self._build_tree(children, child, path)

    def _render_tree(self, tree):
        for group, attrs in tree.items():
            fetch_url = makeuri_contextless(
                request,
                [
                    ("view_name", "aggr_all"),
                    ("aggr_group_tree", "/".join(attrs["__path__"])),
                ],
                filename="view.py",
            )

            if attrs.get('__children__'):
                html.begin_foldable_container(
                    "bi_aggregation_group_trees", group, False,
                    HTML(html.render_a(
                        group,
                        href=fetch_url,
                        target="main",
                    )))
                self._render_tree(attrs['__children__'])
                html.end_foldable_container()
            else:
                html.open_ul()
                bulletlink(group, fetch_url)
                html.close_ul()
