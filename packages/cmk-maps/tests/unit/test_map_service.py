#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio

import pytest
from fake_links import FakeLinkGui

from cmk.maps.backend.schemas.map import MapConfig
from cmk.maps.backend.services import map_service


def test_a_map_is_found_only_under_its_own_owner() -> None:
    map_service.register_map("alice", MapConfig(name="net"))

    assert map_service.get_map("", "net") is None
    assert map_service.get_map("bob", "net") is None


def test_a_link_target_the_daemon_holds_is_not_fetched_again() -> None:
    held = MapConfig(name="net", alias="held")
    map_service.register_map("carol", held)
    gui = FakeLinkGui({("alice", "net"): ("carol", MapConfig(name="net", alias="fetched"))})

    found = asyncio.run(map_service.find_link_targets(gui, "alice", ["net"]))

    assert found == {"net": ("carol", held)}


def test_a_link_target_the_gui_names_no_map_for_is_left_out() -> None:
    map_service.register_map("alice", MapConfig(name="net"))

    assert asyncio.run(map_service.find_link_targets(FakeLinkGui({}), "alice", ["net"])) == {}


def test_a_fetched_link_target_is_fetched_again_after_a_while(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(map_service, "_LINKED_FOR", 0.0)
    gui = FakeLinkGui({("alice", "net"): ("carol", MapConfig(name="net"))})

    asyncio.run(map_service.find_link_targets(gui, "alice", ["net"]))
    asyncio.run(map_service.find_link_targets(gui, "alice", ["net"]))

    assert gui.held == [set(), set()]
