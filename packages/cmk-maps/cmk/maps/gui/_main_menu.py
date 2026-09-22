#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Surface Checkmk Maps in the GUI navigation.

The Maps SPA mounts inside ``maps.py`` and reads its route from query params
(``?name=``/``?mode=``). Map management under *Customize* comes from the
pagetype framework (``MapPage`` is a pagetype, listed like graph collections).
This module only adds the viewable maps under *Monitor*: the core menu builder
calls :func:`monitor_menu_topics` (a no-op without the edition, permission or any
maps). Maps has no *Setup* tile; the image library and any other authoring
surfaces live inside the SPA.
"""

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.sidebar import monitor_menu_topic_registry, MonitorMenuTopicContributor
from cmk.gui.utils.roles import UserPermissions
from cmk.maps.gui.store import get_listable_maps
from cmk.shared_typing.main_menu import DefaultIcon, NavItemTopic, NavItemTopicEntry
from cmk.web.utils.icons import IconNames
from cmk.web.utils.urls import makeuri_contextless

# Menu entries point at the Checkmk page that mounts the SPA inline (keeps the
# main navigation); the route travels in query params (``?name=``/``?mode=``),
# read by the SPA from the URL.
_MAPS_PAGE = "maps.py"


def _iter_maps(user_permissions: UserPermissions) -> list[tuple[str, str]]:
    """Return (name, title) for each map the user may see listed, from the pagetype store.

    Maps are canonical Checkmk pagetypes now, so the menu reads the same
    permission-filtered store the overview does (``MapPage.pages``), not the
    daemon's legacy on-disk files.
    """
    return sorted(
        (
            (page.name(), page.title() or page.name())
            for page in get_listable_maps(user_permissions)
        ),
        key=lambda the_map: the_map[1].lower(),
    )


# ---------------------------------------------------------------------------
# Monitor — one entry per map under a "Maps" topic
# ---------------------------------------------------------------------------


def monitor_menu_topics(user_permissions: UserPermissions) -> list[NavItemTopic]:
    if not user_permissions.user_may(user.id, "maps.use"):
        return []
    maps = _iter_maps(user_permissions)
    if not maps:
        return []
    entries = [
        NavItemTopicEntry(
            id=f"maps_map_{name}",
            title=alias,
            url=makeuri_contextless(request, [("name", name)], filename=_MAPS_PAGE),
            sort_index=(index + 1) * 10,
            is_show_more=False,
            icon=DefaultIcon(id=IconNames.graph),
        )
        for index, (name, alias) in enumerate(maps)
    ]
    return [
        NavItemTopic(
            id="maps",
            title=_("Maps"),
            sort_index=75,
            icon=DefaultIcon(id=IconNames.topic_visualization),
            entries=entries,
        )
    ]


def register() -> None:
    """Contribute Maps' Monitor topics through the sidebar's topic registry.

    The core Monitor-menu builders iterate this registry, so cmk.gui core needs no
    Maps import (mirrors how features register into FolderMenuEntryRegistry). Only
    the editions that ship Maps run this, so Maps stays absent everywhere else.
    """
    monitor_menu_topic_registry.register(
        MonitorMenuTopicContributor(ident="maps", topics=monitor_menu_topics)
    )


# NOTE: Maps has no Setup tile. Like every other visual it carries no monitoring
# configuration of its own; its admin-tunable globals (connections, map/object
# defaults, log level, refresh interval) are native Checkmk global settings under
# the two "Maps" groups in Setup → Global settings (all owned by the feature's own
# ConfigDomainMaps, like liveproxyd/dcd). Those same globals are ALSO reachable
# module-near — the map list's own administration menu links two curated views
# (map/object defaults vs connections/daemon), mirroring DCD's "Host manager
# settings"; see cmk.maps.gui._settings_modes. The image library and the API docs
# are authoring/runtime surfaces of the SPA and the daemon, not Setup config.
