#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon Maps state vocabulary (cmk.maps.shared.states)."""

from cmk.maps.shared.states import (
    CRITICAL_STATES,
    HOST_STATE_MAP,
    SERVICE_STATE_MAP,
    SEVERITY_RANK,
    severity_rank,
)

# The combined SEVERITY_RANK must preserve the worst-state order within each
# scale, so max(states, key=SEVERITY_RANK.get) picks the same winner per scale.
_HOST_STATES = ["PENDING", "UP", "UNREACHABLE", "DOWN"]  # worst last
_SERVICE_STATES = ["PENDING", "OK", "UNKNOWN", "WARNING", "CRITICAL"]  # worst last


def test_state_maps_are_the_livestatus_tokens() -> None:
    assert HOST_STATE_MAP == {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
    assert SERVICE_STATE_MAP == {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}


def test_severity_rank_orders_worst_state_highest() -> None:
    assert severity_rank("CRITICAL") > severity_rank("WARNING")
    assert severity_rank("WARNING") > severity_rank("UNKNOWN")
    assert severity_rank("DOWN") > severity_rank("UP")
    assert severity_rank("OK") == severity_rank("UP") == 0
    assert severity_rank("PENDING") == -1


def test_severity_rank_sinks_unknown_tokens() -> None:
    assert severity_rank("") == -1
    assert severity_rank("NONSENSE") == -1


def test_combined_scale_preserves_per_scale_order() -> None:
    # The combined scale must not change any per-scale worst-state winner.
    for states in (_HOST_STATES, _SERVICE_STATES):
        ranks = [SEVERITY_RANK[s] for s in states]
        assert ranks == sorted(ranks)
        assert max(states, key=lambda s: SEVERITY_RANK.get(s, 0)) == states[-1]


def test_critical_states_set() -> None:
    # Mirrored by CRITICAL_STATES in the frontend's problemState.ts.
    assert frozenset({"CRITICAL", "DOWN", "UNREACHABLE"}) == CRITICAL_STATES
