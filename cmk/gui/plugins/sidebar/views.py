#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections import OrderedDict
from typing import NamedTuple, Dict, List, Tuple, Text
import six

import cmk.gui.config as config
import cmk.gui.views as views
import cmk.gui.dashboard as dashboard
import cmk.gui.pagetypes as pagetypes
from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    visuals_by_topic,
    bulletlink,
    footnotelinks,
)
from cmk.gui.i18n import _
from cmk.gui.globals import html

ViewMenuItem = NamedTuple("ViewMenuItem", [
    ("title", Text),
    ("name", str),
    ("is_view", bool),
    ("url", str),
])


@snapin_registry.register
class Views(SidebarSnapin):
    @staticmethod
    def type_name():
        return "views"

    @classmethod
    def title(cls):
        return _("Views")

    @classmethod
    def description(cls):
        return _("Links to global views and dashboards")

    def show(self):
        for topic, entries in get_view_menu_items().items():
            if entries:
                self._render_topic(topic, entries)

        links = []
        if config.user.may("general.edit_views"):
            if config.debug:
                links.append((_("Export"), "export_views.py"))
            links.append((_("Edit"), "edit_views.py"))
            footnotelinks(links)

    def _render_topic(self, topic, entries):
        # type: (Text, List[ViewMenuItem]) -> None
        container_id = six.ensure_str(re.sub('[^a-zA-Z]', '', topic))
        html.begin_foldable_container(treename="views",
                                      id_=container_id,
                                      isopen=False,
                                      title=topic,
                                      indent=True)

        for item in entries:
            if item.is_view:
                bulletlink(item.title,
                           item.url,
                           onclick="return cmk.sidebar.wato_views_clicked(this)")
            elif "?name=" in item.name:
                bulletlink(item.title, item.url)
            else:
                bulletlink(item.title,
                           item.url,
                           onclick="return cmk.sidebar.wato_views_clicked(this)")

        # TODO: One day pagestypes should handle the complete snapin.
        # for page_type in pagetypes.all_page_types().values():
        #     if issubclass(page_type, pagetypes.PageRenderer):
        #         for t, title, url in page_type.sidebar_links():
        #             if t == topic:
        #                 bulletlink(title, url)

        html.end_foldable_container()


def view_menu_url(name, is_view):
    # type: (str, bool) -> str
    if is_view:
        return "view.py?view_name=%s" % name

    if "?name=" in name:
        return name

    return 'dashboard.py?name=%s' % name


# TODO: Move this to some more generic place
def get_view_menu_items():
    # type: () -> Dict[Text, List[ViewMenuItem]]
    # TODO: One bright day drop this whole visuals stuff and only use page_types
    page_type_topics = {}  # type: Dict[Text, List[Tuple[Text, Text, str, bool]]]
    for page_type in pagetypes.all_page_types().values():
        if issubclass(page_type, pagetypes.PageRenderer):
            for t, title, url in page_type.sidebar_links():
                page_type_topics.setdefault(t, []).append((t, title, url, False))

    visuals_topics_with_entries = visuals_by_topic(
        list(views.get_permitted_views().items()) +
        list(dashboard.get_permitted_dashboards().items()))
    all_topics_with_entries = []
    for topic, entries in visuals_topics_with_entries:
        if topic in page_type_topics:
            entries = entries + page_type_topics[topic]
            del page_type_topics[topic]
        all_topics_with_entries.append((topic, entries))

    all_topics_with_entries += page_type_topics.items()

    # Filter hidden / not permitted entries
    by_topic = OrderedDict()  # type: Dict[Text, List[ViewMenuItem]]
    for topic, entries in all_topics_with_entries:
        for t, title, name, is_view in entries:
            if is_view and config.visible_views and name not in config.visible_views:
                continue
            if is_view and config.hidden_views and name in config.hidden_views:
                continue
            if t != topic:
                continue

            url = view_menu_url(name, is_view)
            by_topic.setdefault(topic, []).append(
                ViewMenuItem(title=title, name=name, is_view=is_view, url=url))

    return by_topic
