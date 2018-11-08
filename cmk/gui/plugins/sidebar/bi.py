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

import cmk.gui.bi as bi
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML

from . import (
    sidebar_snapins,
    bulletlink,
)

#   .--as list-------------------------------------------------------------.
#   |                                   _ _     _                          |
#   |                        __ _ ___  | (_)___| |_                        |
#   |                       / _` / __| | | / __| __|                       |
#   |                      | (_| \__ \ | | \__ \ |_                        |
#   |                       \__,_|___/ |_|_|___/\__|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def render_bi_groups():
    html.open_ul()
    for group in sorted(bi.get_aggregation_group_trees()):
        bulletlink(group, "view.py?view_name=aggr_group&aggr_group=%s" % html.urlencode(group))
    html.close_ul()


sidebar_snapins["biaggr_groups"] = {
    "title": _("BI Aggregation Groups"),
    "description": _("A direct link to all groups of BI aggregations"),
    "render": render_bi_groups,
    "allowed": ["admin", "user", "guest"]
}

#.
#   .--as tree-------------------------------------------------------------.
#   |                                _                                     |
#   |                     __ _ ___  | |_ _ __ ___  ___                     |
#   |                    / _` / __| | __| '__/ _ \/ _ \                    |
#   |                   | (_| \__ \ | |_| | |  __/  __/                    |
#   |                    \__,_|___/  \__|_|  \___|\___|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def render_bi_groups_tree():
    tree = {}
    for group in bi.get_aggregation_group_trees():
        _build_tree(group.split("/"), tree, tuple())
    _render_tree(tree)


def _build_tree(group, parent, path):
    this_node = group[0]
    path = path + (this_node,)
    child = parent.setdefault(this_node, {"__path__": path})
    children = group[1:]
    if children:
        child = child.setdefault('__children__', {})
        _build_tree(children, child, path)


def _render_tree(tree):
    for group, attrs in tree.iteritems():
        fetch_url = html.makeuri_contextless([
            ("view_name", "aggr_all"),
            ("aggr_group_tree", "/".join(attrs["__path__"])),
        ], "view.py")

        if attrs.get('__children__'):
            html.begin_foldable_container(
                "bi_aggregation_group_trees", group, False,
                HTML(html.render_a(
                    group,
                    href=fetch_url,
                    target="main",
                )))
            _render_tree(attrs['__children__'])
            html.end_foldable_container()
        else:
            html.open_ul()
            bulletlink(group, fetch_url)
            html.close_ul()


sidebar_snapins["biaggr_groups_tree"] = {
    "title": _("BI Aggregation Groups Tree"),
    "description": _("A direct link to all groups of BI aggregations organized as tree"),
    "render": render_bi_groups_tree,
    "allowed": ["admin", "user", "guest"]
}
