#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Per-group SSE delta-snapshot garbage collection.

Subscribers join and leave a map's broadcast loop with distinct group keys
(monitoring scope, folder scope, …). The loop must forget a group's delta
snapshot once its last subscriber leaves, otherwise a long-lived NOC map
accumulates dead ``(map, group)`` entries until the whole loop exits.
"""

from cmk.maps.backend.services import state_service


def test_prune_map_snapshots_keeps_live_groups_and_other_maps() -> None:
    snap: dict[tuple[str, str | None], int] = {
        ("b1", "g1"): 1,
        ("b1", "g2"): 2,
        ("b1", None): 3,
        ("b2", "g1"): 4,
    }

    state_service.prune_map_snapshots(snap, "b1", {"g1", None})

    assert snap == {
        ("b1", "g1"): 1,
        ("b1", None): 3,
        ("b2", "g1"): 4,
    }


def test_prune_group_snapshots_covers_all_internal_stores() -> None:
    gone = ("map", "gone")
    alive = ("map", "alive")
    other = ("other", "gone")
    try:
        state_service._state_snapshots[gone] = {}  # noqa: SLF001
        state_service._state_snapshots[alive] = {}  # noqa: SLF001
        state_service._state_snapshots[other] = {}  # noqa: SLF001
        state_service._timing_snapshots[gone] = {}  # noqa: SLF001
        state_service._folder_tree_snapshots[gone] = {}  # noqa: SLF001
        state_service._topology_snapshots[gone] = {}  # noqa: SLF001
        state_service._topology_timing_snapshots[gone] = {}  # noqa: SLF001

        state_service.prune_group_snapshots("map", {"alive"})

        # Stale group dropped from every internal store…
        assert gone not in state_service._state_snapshots  # noqa: SLF001
        assert gone not in state_service._timing_snapshots  # noqa: SLF001
        assert gone not in state_service._folder_tree_snapshots  # noqa: SLF001
        assert gone not in state_service._topology_snapshots  # noqa: SLF001
        assert gone not in state_service._topology_timing_snapshots  # noqa: SLF001
        # …while the live group and a different map are left untouched.
        assert alive in state_service._state_snapshots  # noqa: SLF001
        assert other in state_service._state_snapshots  # noqa: SLF001
    finally:
        for key in (gone, alive, other):
            state_service._state_snapshots.pop(key, None)  # noqa: SLF001
            state_service._timing_snapshots.pop(key, None)  # noqa: SLF001
            state_service._folder_tree_snapshots.pop(key, None)  # noqa: SLF001
            state_service._topology_snapshots.pop(key, None)  # noqa: SLF001
            state_service._topology_timing_snapshots.pop(key, None)  # noqa: SLF001
