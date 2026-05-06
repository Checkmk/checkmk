#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import pytest

from tests.qa_metrics.change_quality.detect_test import (
    attribute_test_for_change,
    has_test_for_paths,
    is_test_path,
)


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


@pytest.mark.parametrize(
    "files_changed",
    [
        (".werks/19499.md",),
        (".werks/19499",),
        (".werks/19499", ".werks/19500.md"),
        (),
    ],
)
def test_attribute_test_for_change_returns_none_when_no_signal(
    files_changed: tuple[str, ...],
) -> None:
    """Werk-add-only commits carry no signal: emit NULL, not False."""
    assert attribute_test_for_change(files_changed) is None


def test_attribute_test_for_change_true_when_test_present() -> None:
    assert (
        attribute_test_for_change((".werks/19499.md", "cmk/foo.py", "tests/unit/cmk/test_foo.py"))
        is True
    )


def test_attribute_test_for_change_false_when_only_non_werk_non_test_files() -> None:
    assert attribute_test_for_change((".werks/19499.md", "cmk/foo.py")) is False
