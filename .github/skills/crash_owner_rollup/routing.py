# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Route a crash group's plugin_path/check_type to a component owner.

Uses `cmk-components info` once per run (cached for a day) to build a
path-prefix -> component index. Generates several candidate paths per group
and picks the most specific component match (falling back to the generic
"plugins" bucket / Plugins coordinator).
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .cache import cache_dir

GENERIC_PLUGINS_ID = "plugins"
COMPONENTS_TTL_SECONDS = 24 * 3600

# Site-local install roots. Plugins whose crashing frame lives here are
# third-party / MKP installs, not shipped Checkmk core (core lives under
# lib/python3/ without a local/ segment). They are filtered out of the rollup.
_LOCAL_INSTALL_MARKERS: tuple[str, ...] = ("/local/lib/python3/", "/local/share/check_mk/")


def is_external_plugin(plugin_path: str) -> bool:
    """True if the crash originates in a site-local (third-party / MKP) plugin."""
    return any(marker in plugin_path for marker in _LOCAL_INSTALL_MARKERS)


# Bare filenames too generic to fuzzy-match against the repo
SKIP_BARE: frozenset[str] = frozenset(
    {
        "__init__.py",
        "check.py",
        "checkers.py",
        "config.py",
        "_check_levels.py",
        "_checking_classes.py",
        "symmetric.py",
        "_file.py",
        "console.py",
        "parameters.py",
        "decoder.py",
        "value_store.py",
        "wmi.py",
    }
)

# Shared-library paths whose family is well-known but not mappable by filename alone
LIB_OVERRIDES: dict[str, str] = {
    "cmk/plugins/lib/diskstat.py": "cmk/plugins/diskstat/",
    "cmk/plugins/lib/wmi.py": "cmk/plugins/windows/",
    "cmk/plugins/lib/mssql_counters.py": "cmk/plugins/mssql/",
    "cmk/plugins/lib/netapp_api.py": "cmk/plugins/netapp/",
}


@dataclass(frozen=True)
class Component:
    id: str
    name: str
    lead: str
    members: tuple[str, ...]
    paths: tuple[str, ...]


@dataclass(frozen=True)
class Route:
    component_id: str
    component_name: str
    lead: str
    matched_path: str


def _components_cache_path() -> Path:
    return cache_dir() / "components.json"


class _ComponentBuilder:
    def __init__(self, name: str, id_: str) -> None:
        self.name = name
        self.id = id_
        self.lead = ""
        self.members: list[str] = []
        self.paths: list[str] = []

    def build(self) -> Component:
        return Component(
            id=self.id,
            name=self.name,
            lead=self.lead,
            members=tuple(self.members),
            paths=tuple(self.paths),
        )


def _parse_info(text: str) -> list[Component]:
    components: list[Component] = []
    cur: _ComponentBuilder | None = None
    mode: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^([^\s\[].+?)\s+\[([a-z0-9_]+)\]\s*$", line)
        if m and not line.startswith(" "):
            if cur is not None:
                components.append(cur.build())
            cur = _ComponentBuilder(name=m.group(1).strip(), id_=m.group(2))
            mode = None
            continue
        if cur is None:
            continue
        stripped = line.lstrip()
        if stripped.startswith("component lead:"):
            cur.lead = stripped.split(":", 1)[1].strip()
            mode = None
            continue
        if stripped.startswith("additional members:"):
            mode = "members"
            continue
        if stripped.startswith("code location:"):
            mode = "paths"
            continue
        if stripped.startswith("- "):
            val = stripped[2:].strip()
            if mode == "members":
                cur.members.append(val)
            elif mode == "paths":
                cur.paths.append(val.lstrip("/"))
    if cur is not None:
        components.append(cur.build())
    return components


def load_components(force_refresh: bool = False) -> tuple[list[Component], list[tuple[str, str]]]:
    """Return (components, path_index). path_index is [(prefix, component_id), ...] sorted desc by length."""
    cache = _components_cache_path()
    now = time.time()
    if (
        not force_refresh
        and cache.is_file()
        and (now - cache.stat().st_mtime) < COMPONENTS_TTL_SECONDS
    ):
        data: dict[str, Any] = json.loads(cache.read_text())
        comps: list[Component] = [
            Component(
                id=str(c["id"]),
                name=str(c["name"]),
                lead=str(c.get("lead", "")),
                members=tuple(c.get("members") or ()),
                paths=tuple(c.get("paths") or ()),
            )
            for c in data["components"]
        ]
        index: list[tuple[str, str]] = [(str(p), str(cid)) for p, cid in data["path_index"]]
        return comps, index

    out = subprocess.run(
        ["cmk-components", "info"], capture_output=True, text=True, check=True, timeout=300
    )
    comps = _parse_info(out.stdout)
    raw_index: list[tuple[str, str]] = []
    for c in comps:
        for p in c.paths:
            raw_index.append((p, c.id))
    raw_index.sort(key=lambda kv: -len(kv[0]))

    cache.write_text(
        json.dumps(
            {
                "generated_at": now,
                "components": [asdict(c) for c in comps],
                "path_index": raw_index,
            },
            indent=2,
        )
    )
    return comps, raw_index


def _candidate_paths(plugin_path: str, check_type: str, repo: Path) -> list[str]:
    """Generate ordered candidate paths for component lookup."""
    p = ""
    if plugin_path:
        m = re.search(r"(cmk(?:_addons)?(?:/.+)?)$", plugin_path)
        if m:
            p = m.group(1)
    cands: list[str] = []

    if p:
        cands.append(p)
        cands.append(p.replace("cmk/plugins/", "packages/cmk-plugins/cmk/plugins/", 1))
        cands.append(
            p.replace("cmk/plugins/", "non-free/packages/cmk-plugins-nonfree/cmk/plugins/", 1)
        )
        m2 = re.match(r"cmk_addons/plugins/([^/]+)/", p)
        if m2:
            x = m2.group(1)
            cands.append(p.replace(f"cmk_addons/plugins/{x}/", f"cmk/plugins/{x}/", 1))
            cands.append(
                p.replace(
                    f"cmk_addons/plugins/{x}/",
                    f"packages/cmk-plugins/cmk/plugins/{x}/",
                    1,
                )
            )

    if check_type:
        cands.append(f"cmk/legacy_checks/{check_type}.py")
        cands.append(f"cmk/plugins/{check_type}/")
        cands.append(f"packages/cmk-plugins/cmk/plugins/{check_type}/")
        parts = check_type.split("_")
        for i in range(len(parts) - 1, 0, -1):
            head = "_".join(parts[:i])
            cands.append(f"cmk/plugins/{head}/")
            cands.append(f"packages/cmk-plugins/cmk/plugins/{head}/")

    if p:
        m3 = re.match(r"cmk/plugins/(?:collection|lib)/(?:agent_based/)?([^/]+)\.py$", p)
        if m3:
            bare = m3.group(1)
            cands.append(f"cmk/plugins/{bare}/")
            cands.append(f"packages/cmk-plugins/cmk/plugins/{bare}/")
            parts = bare.split("_")
            for i in range(len(parts) - 1, 0, -1):
                head = "_".join(parts[:i])
                cands.append(f"cmk/plugins/{head}/")
                cands.append(f"packages/cmk-plugins/cmk/plugins/{head}/")

        bare = p.rsplit("/", 1)[-1]
        if bare not in SKIP_BARE:
            for hit in _find_by_bare(bare, repo):
                cands.append(hit)

    if p in LIB_OVERRIDES:
        cands.insert(0, LIB_OVERRIDES[p])

    # Dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _find_by_bare(filename: str, repo: Path) -> list[str]:
    if not filename:
        return []
    hits = list(repo.glob(f"cmk/plugins/**/{filename}"))
    hits += list(repo.glob(f"packages/cmk-plugins/cmk/plugins/**/{filename}"))
    hits = [h for h in hits if "__pycache__" not in str(h) and "/tests/" not in str(h)]
    hits.sort(key=lambda h: (0 if "/agent_based/" in str(h) else 1, len(str(h))))
    return [str(h.relative_to(repo)) for h in hits]


def _match(path: str, index: list[tuple[str, str]]) -> tuple[str, str] | None:
    p = path.lstrip("/")
    for prefix, cid in index:
        if prefix.endswith("*"):
            if p.startswith(prefix[:-1]):
                return cid, prefix
        elif p == prefix or p.startswith(prefix + "/"):
            return cid, prefix
    return None


def route_group(
    plugin_path: str,
    check_type: str,
    components_by_id: dict[str, Component],
    path_index: list[tuple[str, str]],
    repo: Path,
) -> Route | None:
    """Return the best component match for a group, preferring specific over generic."""
    fallback: tuple[str, str] | None = None
    for cand in _candidate_paths(plugin_path, check_type, repo):
        hit = _match(cand, path_index)
        if hit is None:
            continue
        cid, _ = hit
        if cid == GENERIC_PLUGINS_ID:
            if fallback is None:
                fallback = (cid, cand)
            continue
        c = components_by_id[cid]
        return Route(c.id, c.name, c.lead, cand)
    if fallback is not None:
        cid, cand = fallback
        c = components_by_id[cid]
        return Route(c.id, c.name, c.lead, cand)
    return None
