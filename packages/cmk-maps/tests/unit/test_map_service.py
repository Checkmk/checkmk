#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio

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


def test_a_fetched_link_target_is_fetched_again_after_a_while() -> None:
    gui = FakeLinkGui({("alice", "net"): ("carol", MapConfig(name="net"))})
    a_day = 24 * 3600.0

    asyncio.run(map_service.find_link_targets(gui, "alice", ["net"], clock=lambda: 0.0))
    asyncio.run(map_service.find_link_targets(gui, "alice", ["net"], clock=lambda: a_day))

    assert gui.held == [set(), set()]


def test_an_unsaved_preview_lets_no_older_signed_config_in() -> None:
    assert map_service.register_signed_map("alice", MapConfig(name="net", version=2))
    map_service.register_map("alice", MapConfig(name="net", alias="preview"))

    assert not map_service.register_signed_map("alice", MapConfig(name="net", version=1))
    assert map_service.register_signed_map("alice", MapConfig(name="net", version=2))
    assert map_service.register_signed_map("bob", MapConfig(name="net", version=1))


def test_a_streamed_map_stays_cached_however_many_maps_are_registered() -> None:
    map_service.register_map("alice", MapConfig(name="streamed"))
    streamed = ("alice", "streamed")

    for i in range(2000):
        map_service.register_map("bob", MapConfig(name=f"m{i}"), pinned=streamed.__eq__)

    assert map_service.get_map("alice", "streamed") is not None
    assert map_service.get_map("bob", "m0") is None
    assert map_service.get_map("bob", "m1999") is not None


def test_maps_past_the_weight_bound_push_out_the_oldest_unstreamed_one() -> None:
    half = map_service.CACHE_MAX_WEIGHT // 2 + 1
    streamed = ("alice", "streamed")
    map_service.register_map("alice", MapConfig(name="streamed"), size=half)
    map_service.register_map("alice", MapConfig(name="old"), size=half, pinned=streamed.__eq__)

    map_service.register_map("alice", MapConfig(name="new"), size=half, pinned=streamed.__eq__)

    assert map_service.get_map("alice", "streamed") is not None
    assert map_service.get_map("alice", "old") is None
    assert map_service.get_map("alice", "new") is not None


def test_a_map_registered_again_counts_its_bytes_once() -> None:
    almost_all = map_service.CACHE_MAX_WEIGHT - 1
    map_service.register_map("alice", MapConfig(name="kept"), size=1)
    for _ in range(3):
        map_service.register_map("alice", MapConfig(name="big"), size=almost_all)

    assert map_service.get_map("alice", "kept") is not None


def test_a_map_read_since_is_pushed_out_after_one_that_was_not() -> None:
    map_service.register_map("alice", MapConfig(name="read"), size=1)
    map_service.register_map("alice", MapConfig(name="unread"), size=1)
    map_service.get_map("alice", "read")

    map_service.register_map("alice", MapConfig(name="new"), size=map_service.CACHE_MAX_WEIGHT - 1)

    assert map_service.get_map("alice", "read") is not None


def _with_hosts(name: str, count: int) -> MapConfig:
    objects = [{"id": f"h{i}", "type": "host", "host_name": f"h{i}"} for i in range(count)]
    return MapConfig.model_validate({"name": name, "objects": objects})


def test_the_objects_of_a_map_count_beyond_its_bytes() -> None:
    half = map_service.CACHE_MAX_WEIGHT // 2
    map_service.register_map("alice", MapConfig(name="old"), size=1)

    map_service.register_map("alice", _with_hosts("first", 5000), size=half)
    map_service.register_map("alice", _with_hosts("second", 5000), size=half - 1)

    assert map_service.get_map("alice", "old") is None
