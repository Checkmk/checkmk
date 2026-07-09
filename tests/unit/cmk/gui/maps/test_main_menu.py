#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""Tests for the Maps Monitor-menu topics."""

from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.permissions import permission_registry
from cmk.gui.sidebar import (
    monitor_menu_topic_registry,
    MonitorMenuTopicContributor,
    registered_monitor_menu_topics,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.maps.gui._main_menu import monitor_menu_topics
from cmk.maps.gui.store import save_map


def _user_permissions() -> UserPermissions:
    return UserPermissions.from_config(active_config, permission_registry)


def test_admin_gets_a_maps_topic_with_the_builtin_maps(
    request_context: None,
    with_admin_login: UserId,
) -> None:
    topics = monitor_menu_topics(_user_permissions())
    assert len(topics) == 1
    topic = topics[0]
    assert topic.id == "maps"
    entry_ids = {entry.id for entry in topic.entries}
    # Every shipped built-in the admin may see becomes a Monitor entry.
    assert "maps_map_all_hosts" in entry_ids
    assert "maps_map_noc_wall" in entry_ids


def test_entries_are_sorted_by_title(
    request_context: None,
    with_admin_login: UserId,
) -> None:
    entries = monitor_menu_topics(_user_permissions())[0].entries
    titles = [entry.title for entry in entries]
    assert titles == sorted(titles, key=str.lower)


def test_hidden_map_gets_no_monitor_entry(
    request_context: None,
    with_admin_login: UserId,
) -> None:
    # "Show this map in the maps list" off keeps the map out of the navigation;
    # it stays reachable by direct link.
    save_map(
        with_admin_login,
        "hidden_map",
        {
            "name": "hidden_map",
            "alias": "Hidden map",
            "connection_id": "cmk_heute",
            "objects": [],
            "view": {"type": "flow"},
            "show_in_lists": False,
        },
        public=False,
    )

    entry_ids = {entry.id for entry in monitor_menu_topics(_user_permissions())[0].entries}
    assert "maps_map_hidden_map" not in entry_ids
    assert "maps_map_all_hosts" in entry_ids  # the shipped built-ins are unaffected


def test_maps_topics_are_discovered_only_through_the_registry(
    request_context: None,
    with_admin_login: UserId,
) -> None:
    # The decoupling contract: cmk.gui core surfaces Maps' Monitor topics via the
    # registry, never via an import. A contributor's topics show up in the merged
    # list the core menu builders consume.
    monitor_menu_topic_registry.register(
        MonitorMenuTopicContributor(ident="maps_test", topics=monitor_menu_topics)
    )
    try:
        topic_ids = {topic.id for topic in registered_monitor_menu_topics(_user_permissions())}
    finally:
        monitor_menu_topic_registry.unregister("maps_test")
    assert "maps" in topic_ids
