#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

        by_topic = visuals_by_topic(dashboard.get_permitted_dashboards().items(),
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
