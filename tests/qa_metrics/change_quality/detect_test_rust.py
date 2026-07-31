#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Detect Rust inline-test signal that ``detect_test.py``'s path heuristic misses.

Rust unit tests live inside the same source file as the code they test
(``#[cfg(test)] mod tests { ... }``), so a commit that fixes a bug and
adds/updates a test in one ``.rs`` file carries no path-level signal --
``detect_test.is_test_path`` never matches a plain ``src/foo.rs``.

Called only as a narrow, lazy fallback from ``push.py``: after the cheap
path-based check has already run and found nothing, and only for commits
that touch at least one ``.rs`` file. Fetches one targeted, path-scoped,
zero-context diff for that single commit (not a full-history walk) and
looks for two kinds of signal:

* A new test was added -- ``#[test]`` / ``#[cfg(test)]`` / ``#[tokio::test(...)]``
  matched against *added* diff lines only, so editing an unrelated line in a
  file that already has tests elsewhere doesn't false-positive.
* An existing test was modified -- inferred from the hunk header's
  function-context annotation (the text git prints after the second ``@@``),
  which names the enclosing ``mod``/``fn``/``impl`` regardless of how far the
  changed line is from it. Matched by the name containing "test" rather than
  a fixed module name, since this codebase doesn't use one canonical name
  (e.g. ``mod test_cn_no_uuid`` in cmk-agent-ctl, not ``mod tests``).
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

_NEW_TEST_PAT = re.compile(r"^\+\s*#\[(?:test|cfg\(test\)|tokio::test(?:\(.*\))?)\]")
_HUNK_HEADER_PAT = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@\s?(.*)$")
_TEST_SCOPE_PAT = re.compile(
    r"^(?:pub(?:\([^)]*\))?\s+)?(?:mod|fn|impl)\s+(?:\w+_)?tests?(?:_\w+|\b)"
)


def attribute_rust_test_touch(repo: Path, sha: str, files_changed: Sequence[str]) -> bool:
    """True if ``sha``'s diff to its ``.rs`` paths added or touched a test.

    Returns ``False`` immediately, with no subprocess call, when ``files_changed``
    has no ``.rs`` path. Otherwise fetches a single, path-scoped, zero-context
    diff for ``sha`` -- cheap relative to a full-history walk, since callers
    only invoke this for the small subset of commits that touch a Rust file
    and got no signal from the path-based heuristic.
    """
    rust_paths = [p for p in files_changed if p.endswith(".rs")]
    if not rust_paths:
        return False
    proc = subprocess.run(
        ["git", "show", "--unified=0", "--format=", sha, "--", *rust_paths],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return _has_test_signal(proc.stdout)


def _has_test_signal(diff_text: str) -> bool:
    for line in diff_text.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            if _NEW_TEST_PAT.match(line):
                return True
            continue
        if (m := _HUNK_HEADER_PAT.match(line)) is not None and _TEST_SCOPE_PAT.match(m.group(1)):
            return True
    return False
