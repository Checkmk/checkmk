#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from tests.qa_metrics.change_quality.components import lookup_components, pick_component


def _touch(repo: Path, *paths: str) -> None:
    for p in paths:
        (repo / p).parent.mkdir(parents=True, exist_ok=True)
        (repo / p).write_text("")


def test_lookup_components_parses_script_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _touch(
        tmp_path,
        "cmk/gui/main.py",
        "cmk/base/config.py",
        "cmk/plugins/aws/agent_based/check.py",
    )
    captured: dict[str, Any] = {}

    def fake_run(args: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = list(args)
        return subprocess.CompletedProcess(
            args=list(args),
            returncode=0,
            stdout=(
                "cmk/gui/main.py: ui_framework\n"
                "cmk/base/config.py: null\n"
                "cmk/plugins/aws/agent_based/check.py: plugins_aws\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = lookup_components(
        ["cmk/gui/main.py", "cmk/base/config.py", "cmk/plugins/aws/agent_based/check.py"],
        tmp_path,
    )

    assert result == {
        "cmk/gui/main.py": "ui_framework",
        "cmk/base/config.py": None,
        "cmk/plugins/aws/agent_based/check.py": "plugins_aws",
    }
    assert captured["args"][:2] == ["cmk-components", "component"]


def test_lookup_components_skips_paths_not_on_disk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Paths that no longer exist on HEAD must be skipped before invocation,
    otherwise cmk-components 404s and aborts the whole batch."""
    _touch(tmp_path, "cmk/gui/main.py")  # only this one exists
    captured: dict[str, Any] = {}

    def fake_run(args: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = list(args)
        return subprocess.CompletedProcess(
            args=list(args),
            returncode=0,
            stdout="cmk/gui/main.py: ui_framework\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = lookup_components(["cmk/gui/main.py", ".werks/19703.md"], tmp_path)
    assert result == {"cmk/gui/main.py": "ui_framework", ".werks/19703.md": None}
    # Only the existing path was passed to cmk-components.
    assert ".werks/19703.md" not in captured["args"]
    assert "cmk/gui/main.py" in captured["args"]


def test_lookup_components_skips_non_utf8_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Files that fail UTF-8 decode crash cmk-components -- skip them.

    Covers two real-world cases we've seen in master:
      * binary files (PDF, PNG) -- raw bytes that aren't UTF-8
      * text-in-non-UTF-8 (latin-1 PowerShell, EBCDIC z/OS agents)
    """
    (tmp_path / "cmk").mkdir()
    (tmp_path / "cmk" / "ok.py").write_text("def f(): pass\n", encoding="utf-8")
    (tmp_path / "cmk" / "blob.png").write_bytes(b"\x89PNG\r\n\x00\x00\x00\x0d")
    # latin-1 file: 0xb4 (acute accent) is an invalid UTF-8 start byte
    (tmp_path / "cmk" / "script.ps1").write_bytes(b"echo `\xb4hello`\n")
    captured: dict[str, Any] = {}

    def fake_run(args: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = list(args)
        return subprocess.CompletedProcess(
            args=list(args),
            returncode=0,
            stdout="cmk/ok.py: ui_framework\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = lookup_components(["cmk/ok.py", "cmk/blob.png", "cmk/script.ps1"], tmp_path)
    assert result == {
        "cmk/ok.py": "ui_framework",
        "cmk/blob.png": None,
        "cmk/script.ps1": None,
    }
    assert "cmk/blob.png" not in captured["args"]
    assert "cmk/script.ps1" not in captured["args"]


def test_lookup_components_aborts_on_nonzero_rc(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failing cmk-components invocation must raise, not silently NULL-fill."""
    _touch(tmp_path, "cmk/ok.py")

    def fake_run(args: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(args),
            returncode=1,
            stdout="",
            stderr="UnicodeDecodeError: invalid byte\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match=r"cmk-components exited rc=1"):
        lookup_components(["cmk/ok.py"], tmp_path)


def test_lookup_components_empty_input(tmp_path: Path) -> None:
    assert lookup_components([], tmp_path) == {}


def test_lookup_components_batches_to_avoid_arg_max(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Inputs above ``batch_size`` must split across multiple subprocess calls.

    Real-world trigger: a single commit that touches thousands of files
    (vendored dep update, mass refactor) would otherwise overflow OS argv
    limits and crash the whole metric.
    """
    paths = [f"cmk/pkg{i}/main.py" for i in range(5)]
    _touch(tmp_path, *paths)
    calls: list[list[str]] = []

    def fake_run(args: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        positional = list(args[4:])  # drop ["cmk-components", "component", "--mode", "script"]
        stdout = "".join(f"{p}: stub\n" for p in positional)
        return subprocess.CompletedProcess(args=list(args), returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = lookup_components(paths, tmp_path, batch_size=2)

    assert len(calls) == 3, calls  # 5 paths / batch=2 -> 2 + 2 + 1
    assert {len(c) - 4 for c in calls} == {1, 2}
    assert result == dict.fromkeys(paths, "stub")


def test_pick_component_picks_majority() -> None:
    files = ["cmk/gui/a.py", "cmk/gui/b.py", "cmk/base/c.py"]
    component_map = {
        "cmk/gui/a.py": "ui_framework",
        "cmk/gui/b.py": "ui_framework",
        "cmk/base/c.py": "automation_engine",
    }
    assert pick_component(files, component_map) == "ui_framework"


def test_pick_component_ignores_test_paths() -> None:
    files = ["tests/unit/test_x.py", "tests/unit/test_y.py", "cmk/base/c.py"]
    component_map = {
        "tests/unit/test_x.py": "ui_framework",
        "tests/unit/test_y.py": "ui_framework",
        "cmk/base/c.py": "automation_engine",
    }
    assert pick_component(files, component_map) == "automation_engine"


def test_pick_component_returns_none_when_all_paths_unmapped() -> None:
    files = ["cmk/gui/main.py", "cmk/base/config.py"]
    component_map: dict[str, str | None] = {
        "cmk/gui/main.py": None,
        "cmk/base/config.py": None,
    }
    assert pick_component(files, component_map) is None


def test_pick_component_tie_broken_alphabetically() -> None:
    files = ["cmk/gui/main.py", "cmk/base/config.py"]
    component_map = {
        "cmk/gui/main.py": "ui_framework",
        "cmk/base/config.py": "automation_engine",
    }
    # 1 vs 1 -> alphabetically smallest wins
    assert pick_component(files, component_map) == "automation_engine"
