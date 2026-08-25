#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Smoke tests for the flamegraph tree builder on hand-crafted stats dicts."""

import marshal
from pathlib import Path

import pytest

from cmk.profiling.backend._flamegraph import (
    _make_formatter,
    _MAX_CALLERS_PER_HOTSPOT,
    _MAX_HOTSPOTS,
    _profile_to_folded_stacks,
    build_flamegraph_tree,
    get_top_hotspots,
)

# pstats on-disk shape: {func_key: (prim_calls, ncalls, tottime, cumtime, callers_dict)}
# where func_key is (filename, line, func_name). Note the per-function tuple is
# ordered primitive-then-total, while each caller edge in callers_dict is an
# (ncalls, prim_calls, tottime, cumtime) tuple (total-then-primitive) or a bare
# int when no recursion was recorded.
_FuncKey = tuple[str, int, str]
_CallerEdge = tuple[int, int, float, float] | int
_StatsDict = dict[_FuncKey, tuple[int, int, float, float, dict[_FuncKey, _CallerEdge]]]


def _write_fake_profile(tmp_path: Path, stats: _StatsDict) -> Path:
    """Write a pstats-compatible .profile dump the builder can read."""
    path = tmp_path / "x.profile"
    path.write_bytes(marshal.dumps(stats))
    return path


@pytest.fixture(name="simple_profile")
def _simple_profile(tmp_path: Path) -> Path:
    root: _FuncKey = ("/tmp/a.py", 1, "root_func")
    child: _FuncKey = ("/tmp/a.py", 2, "child_func")
    stats: _StatsDict = {
        root: (1, 1, 0.01, 0.10, {}),
        child: (3, 3, 0.05, 0.08, {root: (3, 3, 0.05, 0.08)}),
    }
    return _write_fake_profile(tmp_path, stats)


def test_build_flamegraph_tree_returns_root(simple_profile: Path) -> None:
    root, total_time = build_flamegraph_tree(simple_profile)
    assert root.name == "root"
    assert total_time >= 0
    # The root has at least one synthesised child corresponding to the recorded root frame.
    assert root.children


def test_get_top_hotspots_sorted_by_self_time(simple_profile: Path) -> None:
    hotspots = get_top_hotspots(simple_profile)
    assert hotspots
    # child_func has tottime 0.05, root_func has 0.01 → child first.
    self_times = [h.self_time_ms for h in hotspots]
    assert self_times == sorted(self_times, reverse=True)


def test_get_top_hotspots_skips_zero_tottime(tmp_path: Path) -> None:
    root: _FuncKey = ("/tmp/a.py", 1, "root_func")
    zero: _FuncKey = ("/tmp/a.py", 2, "zero_func")
    stats: _StatsDict = {
        root: (1, 1, 0.01, 0.10, {}),
        zero: (1, 1, 0.00, 0.05, {root: (1, 1, 0.00, 0.05)}),
    }
    path = _write_fake_profile(tmp_path, stats)
    hotspots = get_top_hotspots(path)
    names = [h.function for h in hotspots]
    assert any("root_func" in n for n in names)
    assert not any("zero_func" in n for n in names)


def test_hotspots_expose_total_and_primitive_calls(tmp_path: Path) -> None:
    """A recursive function reports total calls (nc) plus primitive calls (cc).

    ``rec`` is entered once from ``root`` and then recurses, so pstats records
    primitive=1, total=3. The caller edge from ``rec`` to itself carries the two
    recursive re-entries. Both counts must survive extraction so the frontend can
    render the ``total/primitive`` label that reveals recursion.
    """
    root: _FuncKey = ("/tmp/a.py", 1, "root_func")
    rec: _FuncKey = ("/tmp/a.py", 2, "rec_func")
    stats: _StatsDict = {
        # Function tuple is (primitive, total, tottime, cumtime, callers).
        root: (1, 1, 0.01, 0.10, {}),
        rec: (
            1,
            3,
            0.05,
            0.08,
            # Caller edges are (total, primitive, tottime, cumtime).
            {root: (1, 1, 0.02, 0.08), rec: (2, 1, 0.03, 0.05)},
        ),
    }
    path = _write_fake_profile(tmp_path, stats)
    hotspots = get_top_hotspots(path)

    rec_hotspot = next(h for h in hotspots if "rec_func" in h.function)
    assert rec_hotspot.ncalls == 3
    assert rec_hotspot.primitive_calls == 1

    self_edge = next(c for c in rec_hotspot.top_callers if "rec_func" in c.function)
    assert self_edge.ncalls == 2
    assert self_edge.primitive_calls == 1


def test_get_top_hotspots_caps_hotspots_and_callers(tmp_path: Path) -> None:
    hub: _FuncKey = ("/tmp/a.py", 0, "hub")
    caller_edges: dict[_FuncKey, _CallerEdge] = {}
    stats: _StatsDict = {}
    for i in range(_MAX_HOTSPOTS + 100):
        caller: _FuncKey = ("/tmp/a.py", i + 1, f"c{i}")
        stats[caller] = (1, 1, 0.001, 0.001, {})
        caller_edges[caller] = (1, 1, 0.0, 0.001)
    stats[hub] = (1, 1, 100.0, 100.0, caller_edges)

    hotspots = get_top_hotspots(_write_fake_profile(tmp_path, stats))

    assert len(hotspots) == _MAX_HOTSPOTS
    hub_hotspot = next(h for h in hotspots if "hub" in h.function)
    assert len(hub_hotspot.top_callers) == _MAX_CALLERS_PER_HOTSPOT


def test_folded_stacks_prioritise_heavy_child_with_zero_edge_cumtime() -> None:
    """The heavy subtree must be traversed first even when its edge cumtime is 0.

    cProfile reports a per-caller edge cumtime of 0.0 for the single call into a
    re-entrant entry point (``cmk.base.modes.call``), while the callee's own
    cumtime is the whole program. Ordering children by the edge cumtime sorts the
    heavy subtree last, so a trivial sibling exhausts the traversal budget and the
    real call tree never makes it into the flamegraph. Weighting by the callee's
    own cumtime keeps the heavy branch first.
    """
    entry: _FuncKey = ("/tmp/call.py", 24, "call")
    heavy: _FuncKey = ("/tmp/work.py", 1, "do_work")
    heavy_leaf: _FuncKey = ("/tmp/work.py", 2, "leaf")
    trivial: _FuncKey = ("/tmp/prof.py", 34, "dump_profile")
    stats: _StatsDict = {
        entry: (1, 1, 0.01, 10.00, {}),
        # Edge cumtime 0.0 from the entry point, but a large own cumtime.
        heavy: (1, 1, 0.00, 9.00, {entry: (1, 1, 0.00, 0.00)}),
        heavy_leaf: (1, 1, 9.00, 9.00, {heavy: (1, 1, 9.00, 9.00)}),
        # Trivial sibling with a non-zero edge cumtime.
        trivial: (1, 1, 0.001, 0.001, {entry: (1, 1, 0.001, 0.001)}),
    }

    stacks = _profile_to_folded_stacks(stats, _make_formatter())
    stack_strings = [s for s, _ in stacks]

    assert any("do_work" in s for s in stack_strings)
    heavy_pos = next(i for i, s in enumerate(stack_strings) if "do_work" in s)
    trivial_pos = next(i for i, s in enumerate(stack_strings) if "dump_profile" in s)
    assert heavy_pos < trivial_pos, "heavy subtree must be emitted before the trivial sibling"
