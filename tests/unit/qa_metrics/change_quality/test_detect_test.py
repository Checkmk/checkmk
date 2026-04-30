#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import pytest

from tests.qa_metrics.change_quality.detect_test import has_test_for_paths, is_test_path


@pytest.mark.parametrize(
    "path",
    [
        "tests/unit/cmk/test_foo.py",
        "tests/composition/test_x.py",
        "test/test_legacy.py",
        "cmk/plugins/foo/agent_based/test_check.py",
        "cmk/plugins/foo/agent_based/check_foo_test.py",
        "frontend/src/components/Button.test.tsx",
        "frontend/src/components/Button.spec.ts",
        "frontend/src/__tests__/util.ts",
        "agents/scripts/integration_test.sh",
        "lib/foo_test.go",
    ],
)
def test_is_test_path_positive(path: str) -> None:
    assert is_test_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "cmk/gui/main.py",
        "cmk/base/check_api.py",
        "agents/check_mk_agent.linux",
        ".werks/15155.md",
        "README.md",
        "frontend/src/components/Button.tsx",
        "lib/foo.go",
    ],
)
def test_is_test_path_negative(path: str) -> None:
    assert is_test_path(path) is False


def test_has_test_for_paths_any_match() -> None:
    assert has_test_for_paths(["cmk/gui/main.py", "tests/unit/test_x.py"]) is True


def test_has_test_for_paths_none_match() -> None:
    assert has_test_for_paths(["cmk/gui/main.py", "README.md"]) is False


def test_has_test_for_paths_empty() -> None:
    assert has_test_for_paths([]) is False
