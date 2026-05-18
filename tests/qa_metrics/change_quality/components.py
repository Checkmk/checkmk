#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Resolve source-code components via the canonical ``cmk-components`` tool.

Replaces the earlier regex-based ``classify`` module. ``cmk-components`` is the
authoritative source for component ownership; the trade-off is that it queries
gerrit's REST API per path (cached locally by the tool itself) and only knows
about paths that exist at HEAD.

Two-step flow used by ``push.py``:

1. Walk all commits, collect every unique non-test path → batch a single
   ``cmk-components component --mode json`` invocation to populate a lookup.
2. For each row, ``pick_component(files_changed, lookup)`` returns the majority
   component for that change.

Historical paths that have since been renamed are remapped to their HEAD name
via a one-shot ``git log --diff-filter=R`` scan before being handed to
cmk-components -- otherwise commits older than the last reorganisation of the
codebase classify as ``None`` even when their source file simply moved.
"""

from __future__ import annotations

import codecs
import json
import logging
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path

from .detect_test import is_test_path

logger = logging.getLogger(__name__)

# Cap on how many paths we hand to a single ``cmk-components`` invocation. The
# OS imposes a hard limit on argv length (``ARG_MAX``, typically ~128 KiB on
# Linux) -- a large refactor or vendored-deps commit can easily exceed that
# when every changed file becomes one positional argument. Batch instead.
_CMK_COMPONENTS_BATCH = 500

# Streaming UTF-8 check reads the file in 64 KiB chunks: keeps memory bounded
# even when a commit accidentally introduces a 50 MB binary, while still
# scanning the entire file (which is what cmk-components itself does).
_UTF8_DECODE_CHUNK = 65536


def _is_utf8_decodable(path: Path) -> bool:
    """Return True if ``path``'s contents decode cleanly as UTF-8.

    Mirrors what ``cmk-components`` does: it fetches each file from gerrit
    and decodes it as UTF-8 unconditionally (cwz/gerrit_utils/client.py).
    Anything that fails here would crash the tool with a
    ``UnicodeDecodeError`` and (by aborting the whole batch) lose results
    for every other path. Catches binary files (PDFs, PNGs) AND
    text-in-non-UTF-8 files (latin-1 PowerShell scripts, EBCDIC z/OS
    agents, ...).

    Reads incrementally so a large binary in the change set doesn't spike
    memory just to be rejected.
    """
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        with path.open("rb") as fh:
            while chunk := fh.read(_UTF8_DECODE_CHUNK):
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
    except (OSError, UnicodeDecodeError):
        return False
    return True


def _build_rename_map(repo: Path) -> dict[str, str]:
    """Return ``{historical_path: head_path}`` for paths renamed in HEAD's history.

    Walks every rename event reachable from HEAD (single ``git log
    --diff-filter=R --name-status`` invocation, oldest-first), then collapses
    chains: a file renamed ``A -> B -> C`` produces both ``A -> C`` and
    ``B -> C`` so any historical name resolves directly to its HEAD endpoint.

    Used by :func:`lookup_components` to recover a HEAD name for paths that
    don't exist under their historical name (and would otherwise classify as
    ``None`` because ``cmk-components`` only knows ownership for HEAD). Cannot
    recover deletions without a rename: ``git log --diff-filter=R`` skips
    those.
    """
    proc = subprocess.run(
        ["git", "log", "--reverse", "--diff-filter=R", "--name-status", "--format=", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    direct: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        parts = line.split("\t")
        # Format: ``R<similarity>\t<old>\t<new>`` (e.g. ``R100\told.py\tnew.py``).
        if len(parts) != 3 or not parts[0].startswith("R"):
            continue
        _, old, new = parts
        direct[old] = new
    # Collapse multi-step chains so every key points at its final HEAD name.
    collapsed: dict[str, str] = {}
    for start in direct:
        if start in collapsed:
            continue
        chain: list[str] = []
        cur = start
        while cur in direct and cur not in chain:
            chain.append(cur)
            cur = direct[cur]
        for p in chain:
            collapsed[p] = cur
    return collapsed


def lookup_components(
    paths: Iterable[str],
    repo: Path,
    *,
    batch_size: int = _CMK_COMPONENTS_BATCH,
) -> dict[str, str | None]:
    """Return ``{path: component_name_or_None}`` for ``paths``.

    Resolution is keyed by the HEAD-equivalent of each input path:

    * If ``path`` exists on disk in ``repo``, it's queried as-is.
    * If ``path`` doesn't exist but was renamed (per ``git log --diff-filter=R``)
      to a path that exists on HEAD, the renamed target is queried and the
      result is mapped back to the original ``path``. Recovers historical paths
      that simply moved (e.g. ``cmk/legacy_checks/*.py`` → ``cmk/plugins/*``).
    * Otherwise ``path`` resolves to ``None`` -- ``cmk-components`` can't
      classify it (deleted without rename / never on HEAD).

    Resolved HEAD paths are batched into chunks of ``batch_size`` to stay under
    the OS ``ARG_MAX`` limit and handed to ``cmk-components component --mode
    json``; the JSON output's ``null`` deserialises directly to Python ``None``.
    Additionally filtered to UTF-8-decodable files (cmk-components reads file
    content from gerrit and decodes as UTF-8; binary files would otherwise
    crash the whole batch).

    Raises ``RuntimeError`` if cmk-components exits non-zero on the surviving
    queryable paths -- we never silently return partial data, since that would
    land NULLs in postgres.
    """
    all_paths = sorted(set(paths))
    if not all_paths:
        return {}

    on_head = {p for p in all_paths if (repo / p).is_file()}
    stale = [p for p in all_paths if p not in on_head]

    # Only build the rename map if we have stale paths to remap -- walking all
    # of HEAD's history is multi-second work that's pure overhead when every
    # input is already on HEAD (typical for incremental runs).
    rename_map = _build_rename_map(repo) if stale else {}

    def _head_name(p: str) -> str | None:
        if p in on_head:
            return p
        candidate = rename_map.get(p)
        if candidate is not None and (repo / candidate).is_file():
            return candidate
        return None

    head_name_per_orig = {p: _head_name(p) for p in all_paths}
    # Dedupe across input paths that map to the same HEAD name (rename chains
    # A->C and B->C, or duplicate inputs).
    queryable_set = {
        hp for hp in head_name_per_orig.values() if hp is not None and _is_utf8_decodable(repo / hp)
    }
    queryable = sorted(queryable_set)
    skipped_unresolvable = sum(1 for hp in head_name_per_orig.values() if hp is None)
    skipped_non_utf8 = sum(
        1
        for hp in head_name_per_orig.values()
        if hp is not None and not _is_utf8_decodable(repo / hp)
    )

    result: dict[str, str | None] = dict.fromkeys(all_paths)
    if not queryable:
        return result

    logger.info(
        "Resolving components for %d unique HEAD paths via cmk-components "
        "(from %d input paths; %d unresolvable on HEAD, %d non-UTF-8)",
        len(queryable),
        len(all_paths),
        skipped_unresolvable,
        skipped_non_utf8,
    )
    head_results: dict[str, str | None] = dict.fromkeys(queryable)
    for batch_start in range(0, len(queryable), batch_size):
        batch = queryable[batch_start : batch_start + batch_size]
        proc = subprocess.run(
            ["cmk-components", "component", "--mode", "json", *batch],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"cmk-components exited rc={proc.returncode}. "
                f"Refusing to push partial data. stderr:\n{proc.stderr}"
            )
        # --mode json emits a single ``{path: component | null}`` object for
        # the batch; ``null`` deserialises directly to Python ``None``.
        try:
            batch_results = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"cmk-components --mode json emitted non-JSON output: {e}. "
                f"stdout (first 500 chars):\n{proc.stdout[:500]}"
            ) from e
        for path, component in batch_results.items():
            if path in head_results:
                head_results[path] = component

    for orig, head in head_name_per_orig.items():
        result[orig] = None if head is None else head_results.get(head)
    return result


def pick_component(
    files_changed: Iterable[str],
    component_map: Mapping[str, str | None],
) -> str | None:
    """Return the majority component across non-test paths in ``files_changed``.

    Test-only paths are excluded so test-heavy changes don't classify as
    "tests/...". Ties are broken alphabetically. Returns ``None`` when no
    path resolves to a component.
    """
    counts: dict[str, int] = {}
    for path in files_changed:
        if is_test_path(path):
            continue
        if (component := component_map.get(path)) is None:
            continue
        counts[component] = counts.get(component, 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
