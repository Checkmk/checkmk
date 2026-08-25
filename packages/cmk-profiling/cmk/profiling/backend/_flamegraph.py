#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""cProfile data extraction for the Vue-based flamegraph frontend.

Extracts hotspot data, call trees, and summary statistics from cProfile
.profile files for rendering as interactive flamegraphs in the browser.
"""

import pstats
from collections.abc import Callable
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import cast, NotRequired, TypedDict

from cmk.shared_typing.profiling_flamegraph import CallerInfo, FlamegraphNode, HotspotData

_FuncKey = tuple[str, int, str]
_CallerEdge = tuple[int, int, float, float] | int
_StatsDict = dict[_FuncKey, tuple[int, int, float, float, dict[_FuncKey, _CallerEdge]]]

_MAX_DEPTH = 64
_MAX_STACKS = 50_000
# Each unique function may be expanded up to this many times. K=1 leaves shared
# callees (like isinstance, wrappers) unexpanded at most occurrences → large
# empty areas below them. Unbounded K triggers combinatorial blow-up through
# chains of shared callees. K≈5 covers the top few call sites of typical
# shared functions while keeping the tree size bounded.
_MAX_EXPANSIONS_PER_FUNC = 5
# Bound the serialised response. The per-entry cap is the important one: shared
# callees can accumulate thousands of edges, so it defuses a quadratic blow-up.
# The outer cap only scales the list linearly, so it stays generous.
_MAX_HOTSPOTS = 2000
_MAX_CALLERS_PER_HOTSPOT = 50


class _TreeNode(TypedDict):
    name: str
    value: float
    children: dict[str, _TreeNode]
    total: NotRequired[float]


def get_stats_dict(stats: pstats.Stats) -> _StatsDict:
    return cast(_StatsDict, stats.stats)  # type: ignore[attr-defined]


def get_summary_stats(stats: pstats.Stats) -> tuple[int, int]:
    """Return (total_calls, total_functions).

    ``total_calls`` counts every call including recursive re-entries (pstats' nc),
    matching the headline "N function calls" that cProfile reports.
    """
    stats_dict = get_stats_dict(stats)
    total_calls = sum(entry[1] for entry in stats_dict.values())
    return total_calls, len(stats_dict)


def get_function_paths(stats: pstats.Stats) -> dict[str, str]:
    """Map formatted function name → full source path (empty for builtins).

    Lets the flamegraph tooltip show the full file path that ``_format_func``
    drops from the display label (it keeps only the basename so labels fit in
    flamegraph rects).
    """
    stats_dict = get_stats_dict(stats)
    format_func = _make_formatter()
    paths: dict[str, str] = {}
    for key in stats_dict:
        filename, _line, _name = key
        if filename in ("~", "<frozen ") or filename.startswith("<"):
            continue
        paths[format_func(key)] = filename
    return paths


def _format_func_uncached(key: _FuncKey) -> str:
    filename, line, func_name = key

    # Clean up built-in / C-level function names
    # "<built-in method builtins.isinstance>" → "isinstance"
    # "<method 'append' of 'list' objects>" → "list.append"
    if func_name.startswith("<built-in method "):
        inner = func_name[len("<built-in method ") :].rstrip(">")
        # "builtins.isinstance" → "isinstance"
        func_name = inner.split(".")[-1] if "." in inner else inner
        return f"{func_name} [builtin]"
    if func_name.startswith("<built-in function "):
        inner = func_name[len("<built-in function ") :].rstrip(">")
        return f"{inner} [builtin]"
    if func_name.startswith("<method '"):
        # "<method 'append' of 'list' objects>" → "list.append"
        parts = func_name.split("'")
        if len(parts) >= 4:
            return f"{parts[3]}.{parts[1]} [builtin]"
        return f"{parts[1]} [builtin]"
    if filename in ("~", "<frozen "):
        # Other internal / frozen modules
        clean = func_name.strip("<>")
        return f"{clean} [internal]"

    short_file = filename.rsplit("/", 1)[-1] if "/" in filename else filename
    return f"{func_name} ({short_file}:{line})"


def _make_formatter() -> Callable[[_FuncKey], str]:
    """Return a per-call ``_format_func`` with its own cache.

    A fresh cache per invocation prevents the process-wide LRU that a
    module-level decorator would create; a long-lived WSGI worker otherwise
    accumulates entries from every profile it ever rendered. ``_format_func``
    is pure, so cross-profile leakage is currently harmless, but scoping the
    cache makes the absence of coupling explicit and bounds memory use.
    """
    return cache(_format_func_uncached)


def _parse_edge(caller_info: _CallerEdge, fallback_cumtime: float) -> tuple[int, int, float]:
    """Return (total_calls, primitive_calls, cumtime_seconds) for one caller edge.

    The per-edge tuple pstats stores is ``(nc, cc, tt, ct)`` — note the call
    counts are ordered total-then-primitive here, the reverse of the per-function
    tuple. The compact int form (no recursion recorded) means total == primitive.
    """
    if isinstance(caller_info, tuple):
        return caller_info[0], caller_info[1], caller_info[3]
    return caller_info, caller_info, fallback_cumtime


def get_top_hotspots(profile_path: Path, *, stats: pstats.Stats | None = None) -> list[HotspotData]:
    """Extract the top functions by self-time from a .profile file.

    Capped at ``_MAX_HOTSPOTS`` entries with ``_MAX_CALLERS_PER_HOTSPOT``
    callers/callees each to bound the serialised response size.
    """
    if stats is None:
        stats = pstats.Stats(str(profile_path))
    stats_dict = get_stats_dict(stats)
    format_func = _make_formatter()

    total_time = sum(entry[2] for entry in stats_dict.values())
    if total_time <= 0:
        return []

    # Build caller→callee map by inverting the callers dicts.
    # pstats stores callers on the callee side; we invert to get callees per caller.
    callees_map: dict[_FuncKey, list[CallerInfo]] = {}
    for func_key, (_, _, _, cumtime, callers) in stats_dict.items():
        for caller_key, caller_info in callers.items():
            edge_ncalls, edge_primitive, edge_cumtime = _parse_edge(caller_info, cumtime)
            callees_map.setdefault(caller_key, []).append(
                CallerInfo(
                    function=format_func(func_key),
                    ncalls=edge_ncalls,
                    primitive_calls=edge_primitive,
                    cumulative_time_ms=edge_cumtime * 1000,
                )
            )

    entries = []
    for func_key, (primitive_calls, ncalls, tottime, cumtime, callers) in stats_dict.items():
        if tottime <= 0:
            continue
        filename, line, func_name = func_key
        clean_name = format_func(func_key)
        short_file = filename.rsplit("/", 1)[-1] if "/" in filename else filename

        caller_list: list[CallerInfo] = []
        for caller_key, caller_info in callers.items():
            c_ncalls, c_primitive, c_cumtime = _parse_edge(caller_info, 0.0)
            caller_list.append(
                CallerInfo(
                    function=format_func(caller_key),
                    ncalls=c_ncalls,
                    primitive_calls=c_primitive,
                    cumulative_time_ms=c_cumtime * 1000,
                )
            )
        caller_list.sort(key=lambda c: c.cumulative_time_ms, reverse=True)
        caller_list = caller_list[:_MAX_CALLERS_PER_HOTSPOT]

        callee_list = sorted(
            callees_map.get(func_key, []),
            key=lambda c: c.cumulative_time_ms,
            reverse=True,
        )[:_MAX_CALLERS_PER_HOTSPOT]

        entries.append(
            HotspotData(
                function=clean_name,
                file=short_file,
                line=line,
                self_time_ms=tottime * 1000,
                self_pct=tottime / total_time * 100,
                cumulative_time_ms=cumtime * 1000,
                cumulative_pct=cumtime / total_time * 100,
                ncalls=ncalls,
                primitive_calls=primitive_calls,
                top_callers=caller_list,
                top_callees=callee_list,
            )
        )

    entries.sort(key=lambda h: h.self_time_ms, reverse=True)
    return entries[:_MAX_HOTSPOTS]


def _profile_to_folded_stacks(
    stats_dict: _StatsDict,
    format_func: Callable[[_FuncKey], str],
) -> list[tuple[str, float]]:
    """Convert pstats data to folded-stack format.

    DFS ordered by cumtime (biggest first) so the heaviest paths are emitted
    before any global cap kicks in. Each function is expanded up to
    ``_MAX_EXPANSIONS_PER_FUNC`` times — enough to populate the top few call
    sites of shared functions without exponential blow-up through chains of
    shared callees.

    Returns a list of (stack_string, tottime) tuples.
    """
    # Build caller -> [(callee, cumtime)] tree.
    #
    # The weight orders children during the DFS below, so the heaviest branch is
    # emitted before the global _MAX_STACKS budget runs out. Weight each edge by
    # the callee's *own* cumtime rather than the per-caller edge cumtime
    # (``caller_info[3]``): cProfile reports the edge cumtime as 0.0 for the
    # single call into a re-entrant entry point (e.g. ``cmk.base.modes.call``),
    # which would sort the program's entire heavy subtree last and let a trivial
    # sibling exhaust the budget through shared builtins — leaving the real call
    # tree missing from the flamegraph. The callee's own cumtime also matches how
    # the frontend sizes frames (``name_to_cumtime``), so traversal priority and
    # render width stay consistent.
    children: dict[_FuncKey, list[tuple[_FuncKey, float]]] = {}
    all_callees: set[_FuncKey] = set()

    for func_key, (_, _, _, cumtime, callers) in stats_dict.items():
        for caller_key in callers:
            children.setdefault(caller_key, [])
            children[caller_key].append((func_key, cumtime))
            all_callees.add(func_key)

    all_funcs = set(stats_dict.keys())
    roots = all_funcs - all_callees
    if not roots:
        roots = set(sorted(all_funcs, key=lambda k: stats_dict[k][3], reverse=True)[:5])

    stacks: list[tuple[str, float]] = []
    expansion_count: dict[_FuncKey, int] = {}

    for root in sorted(roots, key=lambda k: stats_dict.get(k, (0, 0, 0, 0, {}))[3], reverse=True):
        if len(stacks) >= _MAX_STACKS:
            break
        dfs_stack: list[tuple[_FuncKey, int]] = [(root, -1)]
        path: list[str] = []
        # path_set tracks ancestors on the current path (cycle detection)
        path_set: set[_FuncKey] = set()

        while dfs_stack:
            key, child_idx = dfs_stack[-1]

            if child_idx == -1:
                path.append(format_func(key))
                path_set.add(key)

                entry = stats_dict.get(key)
                tottime = entry[2] if entry else 0.0
                stacks.append((";".join(path), tottime))

                if len(stacks) >= _MAX_STACKS:
                    break

                count = expansion_count.get(key, 0)
                if count < _MAX_EXPANSIONS_PER_FUNC and len(path) < _MAX_DEPTH:
                    expansion_count[key] = count + 1
                    child_list = children.get(key, [])
                    valid_children = [
                        (ck, ct)
                        for ck, ct in sorted(child_list, key=lambda x: x[1], reverse=True)
                        if ck in stats_dict and ck not in path_set
                    ]
                else:
                    valid_children = []

                if not valid_children:
                    dfs_stack.pop()
                    path.pop()
                    path_set.discard(key)
                else:
                    dfs_stack[-1] = (key, len(valid_children))
                    for ck, _ in reversed(valid_children):
                        dfs_stack.append((ck, -1))
            else:
                dfs_stack.pop()
                path.pop()
                path_set.discard(key)

    return stacks


def _build_dict_tree(stacks: list[tuple[str, float]]) -> tuple[_TreeNode, float]:
    """Build an internal dict-based tree from folded stacks and propagate totals."""
    root: _TreeNode = {"name": "root", "value": 0.0, "children": {}}
    total_time = 0.0

    for stack_str, time_val in stacks:
        frames = stack_str.split(";")
        node = root
        for frame in frames:
            if frame not in node["children"]:
                node["children"][frame] = {"name": frame, "value": 0.0, "children": {}}
            node = node["children"][frame]
        node["value"] += time_val
        total_time += time_val

    _propagate_iterative(root)
    return root, total_time


def _propagate_iterative(root: _TreeNode) -> None:
    """Compute 'total' for each node iteratively (post-order)."""
    stack: list[tuple[_TreeNode, bool]] = [(root, False)]
    while stack:
        node, processed = stack[-1]
        if processed or not node["children"]:
            stack.pop()
            child_sum = sum(c["total"] for c in node["children"].values() if "total" in c)
            node["total"] = node["value"] + child_sum
        else:
            stack[-1] = (node, True)
            for child in node["children"].values():
                stack.append((child, False))


def build_flamegraph_tree(
    profile_path: Path, *, stats: pstats.Stats | None = None
) -> tuple[FlamegraphNode, float]:
    """Build a flamegraph tree from a cProfile .profile file.

    Returns (root_node, total_time) where total_time is in seconds.
    The tree is serializable to JSON for the Vue frontend.
    """
    if stats is None:
        stats = pstats.Stats(str(profile_path))
    stats_dict = get_stats_dict(stats)

    if not stats_dict:
        return FlamegraphNode(name="root", value=0.0, total=0.0, children=[]), 0.0

    format_func = _make_formatter()
    stacks = _profile_to_folded_stacks(stats_dict, format_func)
    if not stacks:
        return FlamegraphNode(name="root", value=0.0, total=0.0, children=[]), 0.0

    dict_root, _propagated_total = _build_dict_tree(stacks)
    # Authoritative CPU time = sum of each function's exclusive tottime, taken
    # once per unique function. _build_dict_tree's running total adds tottime
    # for every tree position a function occupies, so it inflates whenever
    # _MAX_EXPANSIONS_PER_FUNC lets a shared callee appear in several stacks.
    # Use stats_dict directly so the headline matches cProfile's own total.
    total_time = sum(entry[2] for entry in stats_dict.values())

    # Every occurrence of a function shows the same cumtime from pstats, so the
    # frontend's labels and width ratios stay consistent across the whole tree.
    name_to_cumtime = {format_func(key): entry[3] for key, entry in stats_dict.items()}

    def _to_node(d: _TreeNode) -> FlamegraphNode:
        children = sorted(d["children"].values(), key=lambda c: c["total"], reverse=True)
        propagated = d.get("total", d["value"])
        return FlamegraphNode(
            name=d["name"],
            value=d["value"],
            total=name_to_cumtime.get(d["name"], propagated),
            children=[_to_node(c) for c in children],
        )

    root_node = _to_node(dict_root)
    # The synthetic "root" has no pstats entry, and its propagated total counts
    # shared callees multiple times (once per tree position). Align it with the
    # top-level children's cumtimes so the frontend scales the canvas correctly.
    if root_node.children:
        root_node = replace(root_node, total=sum(c.total for c in root_node.children))
    return root_node, total_time
