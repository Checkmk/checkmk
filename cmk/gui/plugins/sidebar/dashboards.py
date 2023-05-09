#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

import cmk.gui.config as config
import cmk.gui.dashboard as dashboard
from cmk.gui.i18n import _
from cmk.gui.type_defs import TopicMenuTopic
from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    footnotelinks,
    make_topic_menu,
    show_topic_menu,
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
        show_topic_menu(treename="dashboards", menu=self._get_dashboard_menu_items())

        links = []
        if config.user.may("general.edit_dashboards"):
            if config.debug:
                links.append((_("Export"), "export_dashboards.py"))
            links.append((_("Edit"), "edit_dashboards.py"))
            footnotelinks(links)

    def _get_dashboard_menu_items(self) -> List[TopicMenuTopic]:
        return make_topic_menu([
            ("dashboards", e) for e in dashboard.get_permitted_dashboards().items()
        ])
