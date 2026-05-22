# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Local on-disk cache for crash-owner-rollup.

Stores enriched per-group data keyed by group_id, plus snapshots of past runs
for diff computation. Lives under $XDG_CACHE_HOME (or ~/.cache).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CACHE_VERSION = 1


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    d = Path(base) / "cmk-crash-rollup"
    d.mkdir(parents=True, exist_ok=True)
    (d / "snapshots").mkdir(exist_ok=True)
    return d


@dataclass
class EnrichedGroup:
    """Cached enrichment for one crash group.

    Refresh when `num_crashes` from /search differs from cached value.
    """

    group_id: int
    num_crashes: int
    has_24_plus: bool
    check_type: str
    section_name: str
    plugin_path: str
    latest_24_version: str
    last_seen: float = field(default_factory=time.time)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> EnrichedGroup:
        return cls(**d)


def load_enrichment_cache() -> dict[int, EnrichedGroup]:
    f = cache_dir() / "enrichment.json"
    if not f.is_file():
        return {}
    try:
        data: dict[str, Any] = json.loads(f.read_text())
    except json.JSONDecodeError:
        return {}
    if data.get("version") != CACHE_VERSION:
        return {}
    groups: dict[str, dict[str, Any]] = data.get("groups", {})
    return {int(gid): EnrichedGroup.from_json(g) for gid, g in groups.items()}


def save_enrichment_cache(groups: dict[int, EnrichedGroup]) -> None:
    f = cache_dir() / "enrichment.json"
    payload = {
        "version": CACHE_VERSION,
        "groups": {str(gid): g.to_json() for gid, g in groups.items()},
    }
    f.write_text(json.dumps(payload, indent=2))


def write_snapshot(snapshot: dict[str, Any]) -> Path:
    """Write a per-run snapshot and update 'latest.json'."""
    d = cache_dir() / "snapshots"
    stamp = time.strftime("%Y-%m-%dT%H%M%S")
    path = d / f"{stamp}.json"
    path.write_text(json.dumps(snapshot, indent=2))
    (cache_dir() / "latest.json").write_text(
        json.dumps({"path": path.name, "generated_at": snapshot.get("generated_at", "")})
    )
    return path


def load_previous_snapshot(exclude: Path | None = None) -> dict[str, Any] | None:
    """Return the most recent snapshot file's parsed JSON, optionally excluding one path."""
    d = cache_dir() / "snapshots"
    snaps = sorted(d.glob("*.json"))
    if exclude is not None:
        snaps = [s for s in snaps if s != exclude]
    if not snaps:
        return None
    result: dict[str, Any] = json.loads(snaps[-1].read_text())
    return result
