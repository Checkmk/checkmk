#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import request
from cmk.gui.i18n import _
from cmk.gui.plugins.views.icons.utils import Icon, icon_and_action_registry
from cmk.gui.utils.urls import makeuri_contextless


@icon_and_action_registry.register
class ShowParentChildTopology(Icon):
    @classmethod
    def ident(cls):
        return "parent_child_topology"

    @classmethod
    def title(cls) -> str:
        return _("Network Topology")

    def host_columns(self):
        return ["name"]

    def default_sort_index(self):
        return 51

    def render(self, what, row, tags, custom_vars):
        url = makeuri_contextless(
            request,
            [("host_name", row["host_name"])],
            filename="parent_child_topology.py",
        )
        return "aggr", _("Host Parent/Child topology"), url
