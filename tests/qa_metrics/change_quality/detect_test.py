#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Heuristic detection of test files in a list of changed paths.

Mirrors the heuristic from gerrit 133576 / ``bugfix_kpi_trend.py``: presence
of *any* test path in the change is enough to mark it as tested.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_TEST_PAT = re.compile(
    r"(^|/)tests?/"  # .../tests/... or .../test/...
    r"|(^|/)__tests__/"  # Jest __tests__/ convention
    r"|(^|/)test_[^/]+\.(py|sh)$"  # test_<name>.py/sh
    r"|_test\.(py|sh|go)$"  # <name>_test.py/sh/go
    r"|(^|/)tests?\.py$"  # standalone test.py / tests.py modules
    r"|\.(test|spec)\.[tj]sx?$"  # .test.ts / .spec.js / .test.tsx etc.
)


def is_test_path(path: str) -> bool:
    """True if ``path`` matches our test-file heuristic."""
    return _TEST_PAT.search(path) is not None


def has_test_for_paths(paths: Iterable[str]) -> bool:
    """True if any path in ``paths`` matches our test-file heuristic."""
    return any(is_test_path(p) for p in paths)
