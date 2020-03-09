#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.plugins.views.icons import Icon, icon_and_action_registry


@icon_and_action_registry.register
class ShowParentChildTopology(Icon):
    @classmethod
    def ident(cls):
        return "parent_child_topology"

    def host_columns(self):
        return ["name"]

    def default_sort_index(self):
        return 51

    def render(self, what, row, tags, custom_vars):
        url = html.makeuri_contextless([("host_regex", "^%s$" % row["host_name"])],
                                       filename="parent_child_topology.py")
        return "aggr", _("Host Parent/Child topology"), url
