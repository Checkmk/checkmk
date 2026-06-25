#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared GUI↔daemon typed Livestatus-row accessors for Checkmk Maps.

Both the daemon (``cmk.maps.backend``) and the GUI (``cmk.maps.gui``) read
positional cells out of Livestatus rows into typed Python values, defaulting
gracefully when a column is absent or the wrong type. They can't import each
other (module-layer boundary), so the accessors live here in ``cmk.maps.shared`` —
the same seam as ``cmk.maps.shared.states``.

The accessors are type-aware (they dispatch on the value the livestatus client
actually returns — ``str``/``int``/``float``/``list``/``dict``) rather than
coercing everything through ``str()``. A row is any positional sequence, so
this stays a pure ``cmk.maps.shared`` helper with no livestatus-layer dependency.
"""

from collections.abc import Sequence


def row_str(row: Sequence[object], idx: int, default: str = "") -> str:
    if idx >= len(row):
        return default
    v = row[idx]
    return v if isinstance(v, str) else default


def row_int(row: Sequence[object], idx: int, default: int = 0) -> int:
    if idx >= len(row):
        return default
    v = row[idx]
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int | float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return default
    return default


def row_float(row: Sequence[object], idx: int, default: float = 0.0) -> float:
    if idx >= len(row):
        return default
    v = row[idx]
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, int | float):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return default
    return default


def row_bool(row: Sequence[object], idx: int, *, default: bool = True) -> bool:
    if idx >= len(row):
        return default
    return bool(row_int(row, idx, default=1 if default else 0))


def row_float_or_none(row: Sequence[object], idx: int) -> float | None:
    """Return float for the cell, or None when livestatus reports the missing
    sentinel 0 (used for never-checked services) or the column is absent."""
    if idx >= len(row):
        return None
    v = row_float(row, idx, default=0.0)
    return v if v > 0 else None


def row_list(row: Sequence[object], idx: int) -> list[object]:
    if idx >= len(row):
        return []
    v = row[idx]
    return v if isinstance(v, list) else []


def row_dict(row: Sequence[object], idx: int) -> dict[str, object]:
    if idx >= len(row):
        return {}
    v = row[idx]
    return v if isinstance(v, dict) else {}


def row_strs(row: Sequence[object], idx: int) -> list[str]:
    """Return a string list from a Livestatus list-typed column."""
    return [str(x) for x in row_list(row, idx) if x]
