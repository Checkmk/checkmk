#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Resolve source-code components via the canonical ``cmk-components`` tool.

Replaces the earlier regex-based ``classify`` module. ``cmk-components`` is the
authoritative source for component ownership; the trade-off is that it queries
gerrit's REST API per path (cached locally by the tool itself).

Two-step flow used by ``push.py``:

1. Walk all commits, collect every unique non-test path → batch a single
   ``cmk-components component --mode json`` invocation to populate a lookup.
2. For each row, ``pick_component(files_changed, lookup)`` returns the majority
   component for that change.
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


def lookup_components(
    paths: Iterable[str],
    repo: Path,
    *,
    batch_size: int = _CMK_COMPONENTS_BATCH,
) -> dict[str, str | None]:
    """Return ``{path: component_name_or_None}`` for ``paths``.

    Invokes ``cmk-components component --mode json`` -- batched into
    chunks of ``batch_size`` to stay under the OS ``ARG_MAX`` limit -- for
    every path that (a) exists on disk in ``repo`` and (b) looks like a
    text file. Paths that don't satisfy both get ``None`` without ever
    being asked, which avoids two classes of cmk-components failure:

    * 404 on paths missing from HEAD (e.g. werk files since renamed).
    * ``UnicodeDecodeError`` on binary files (cmk-components reads file
      content from gerrit and decodes it as UTF-8).

    Raises ``RuntimeError`` if cmk-components exits non-zero on the
    surviving (text + on-HEAD) paths -- we never silently return partial
    data, since that would land NULLs in postgres.
    """
    all_paths = sorted(set(paths))
    if not all_paths:
        return {}

    queryable = [p for p in all_paths if (repo / p).is_file() and _is_utf8_decodable(repo / p)]
    skipped = len(all_paths) - len(queryable)
    result: dict[str, str | None] = dict.fromkeys(all_paths)
    if not queryable:
        return result

    logger.info(
        "Resolving components for %d/%d unique paths via cmk-components "
        "(skipped %d missing-on-HEAD / not-UTF-8)",
        len(queryable),
        len(all_paths),
        skipped,
    )
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
        # the batch; ``null`` deserialises directly to Python ``None``. No
        # terminal-formatted output means no $COLUMNS-dependent wrapping
        # and no string sentinels to special-case.
        try:
            batch_results = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"cmk-components --mode json emitted non-JSON output: {e}. "
                f"stdout (first 500 chars):\n{proc.stdout[:500]}"
            ) from e
        for path, component in batch_results.items():
            if path in result:
                result[path] = component
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
