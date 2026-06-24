#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Fingerprint helpers used by the crash report store for write-time deduplication.

A fingerprint is the deduplication key for a crash (crash type, exception type,
and the (file, lineno) of each traceback frame). The on-disk ``.fingerprint_index``
maps the stable hash of a fingerprint to the crash directory that holds the first
occurrence, so repeated crashes merge into one directory instead of piling up."""

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from cmk.ccc import store

from ._crash import CrashOccurrences

_FINGERPRINT_INDEX_FILE: Final = ".fingerprint_index"


def crash_fingerprint(
    crash_type: str, exc_traceback: Sequence[tuple[str, int, str, str]], exc_type: str | None
) -> tuple[str, str | None, tuple[tuple[str, int], ...]]:
    """Return a deduplication key for a crash: crash type, exception type, and (file, lineno) per frame."""
    frames = tuple((t[0], t[1]) for t in exc_traceback)
    return crash_type, exc_type, frames


def normalize_crash_time(raw_time: object) -> CrashOccurrences:
    """Normalize the time field of a crash report to CrashOccurrences.

    Handles the new dict format as well as the legacy float format from older
    crash.info files, where a single timestamp was stored directly.
    """
    if isinstance(raw_time, dict):
        return CrashOccurrences(
            first_seen=float(raw_time["first_seen"]),
            last_seen=float(raw_time["last_seen"]),
            count=int(raw_time["count"]),
        )
    if isinstance(raw_time, int | float):
        ts = float(raw_time)
        return CrashOccurrences(first_seen=ts, last_seen=ts, count=1)
    raise TypeError(f"time field in crash report is in an unexpected format: {raw_time!r}")


def fingerprint_hash(
    fingerprint: tuple[str, str | None, tuple[tuple[str, int], ...]],
) -> str:
    """Stable hex digest for a crash fingerprint, used as key in the on-disk index."""
    raw = json.dumps(fingerprint, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _load_fingerprint_index(base_dir: Path) -> dict[str, str]:
    """Read the fingerprint→dir_name index from disk. Returns an empty dict if absent."""
    try:
        result: dict[str, str] = json.loads(
            store.load_text_from_file(base_dir / _FINGERPRINT_INDEX_FILE)
        )
        return result
    except Exception:
        return {}


def _save_fingerprint_index(base_dir: Path, index: dict[str, str]) -> None:
    store.save_text_to_file(
        base_dir / _FINGERPRINT_INDEX_FILE,
        json.dumps(index) + "\n",
    )


def _drop_from_index(index: dict[str, str], dir_name: str) -> None:
    """Remove the index entry pointing at ``dir_name`` (if any) to keep it in sync with disk."""
    for fp_hash, name in list(index.items()):
        if name == dir_name:
            del index[fp_hash]
            break
