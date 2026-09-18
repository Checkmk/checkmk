#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
from pathlib import Path

import pytest

from tests.qa_metrics.test_coverage._file_lists import existing, source_paths, tracked_files


def _labels_file(tmp_path: Path, *labels: str) -> Path:
    path = tmp_path / "labels.txt"
    path.write_text("".join(f"{label}\n" for label in labels))
    return path


def test_source_paths_resolves_a_label_to_its_file(tmp_path: Path) -> None:
    """The colon separates the package from the path inside it."""
    _repo_with_a_deleted_file(tmp_path)
    labels = _labels_file(tmp_path, "//cmk:kept.py")
    assert source_paths(labels, tmp_path) == [Path("cmk/kept.py")]


def test_source_paths_resolves_a_label_naming_a_subdirectory(tmp_path: Path) -> None:
    """Only the package is spelled out as a directory; the rest sits after the colon."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "cmk/gui").mkdir(parents=True)
    (tmp_path / "cmk/gui/a.py").touch()
    _git(tmp_path, "add", "-A")
    labels = _labels_file(tmp_path, "//cmk:gui/a.py")
    assert source_paths(labels, tmp_path) == [Path("cmk/gui/a.py")]


def test_source_paths_drops_a_label_with_no_tracked_file(tmp_path: Path) -> None:
    """Generated sources -- doctest runners, entry-point shims -- carry no line count."""
    _repo_with_a_deleted_file(tmp_path)
    labels = _labels_file(tmp_path, "//cmk:kept.py", "//cmk:doctest-doctest-runner.py")
    assert source_paths(labels, tmp_path) == [Path("cmk/kept.py")]


def test_source_paths_ignores_a_line_that_is_not_a_label(tmp_path: Path) -> None:
    """`bazel query` output reaches here with the Aspect CLI's own noise still in it."""
    _repo_with_a_deleted_file(tmp_path)
    labels = _labels_file(tmp_path, "Loading: 3 packages loaded", "//cmk:kept.py", "")
    assert source_paths(labels, tmp_path) == [Path("cmk/kept.py")]


def test_existing_keeps_a_path_with_a_file(tmp_path: Path) -> None:
    (tmp_path / "cmk").mkdir()
    (tmp_path / "cmk/a.py").touch()
    assert existing(tmp_path, [Path("cmk/a.py")]) == [Path("cmk/a.py")]


def test_existing_drops_a_path_deleted_from_the_working_tree(tmp_path: Path) -> None:
    """``git ls-files`` answers from the index, so such a path reaches here."""
    (tmp_path / "cmk").mkdir()
    (tmp_path / "cmk/a.py").touch()
    assert existing(tmp_path, [Path("cmk/a.py"), Path("cmk/gone.py")]) == [Path("cmk/a.py")]


def test_existing_reports_what_it_dropped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A stale list would otherwise shrink the denominator with nothing saying why."""
    assert existing(tmp_path, [Path("cmk/gone.py")]) == []
    assert "cmk/gone.py" in capsys.readouterr().err


def test_existing_says_nothing_when_every_path_is_present(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "cmk").mkdir()
    (tmp_path / "cmk/a.py").touch()
    existing(tmp_path, [Path("cmk/a.py")])
    assert capsys.readouterr().err == ""


def test_existing_drops_a_directory(tmp_path: Path) -> None:
    """Only a file carries executable lines."""
    (tmp_path / "cmk").mkdir()
    assert existing(tmp_path, [Path("cmk")]) == []


def _git(root: Path, *args: str) -> None:
    """Run git with nothing of the developer's environment reaching it."""
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        env={"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_GLOBAL": "/dev/null"},
    )


def _repo_with_a_deleted_file(root: Path) -> None:
    _git(root, "init", "-q")
    (root / "cmk").mkdir()
    (root / "cmk" / "kept.py").touch()
    (root / "cmk" / "gone.py").touch()
    (root / "doc").mkdir()
    (root / "doc" / "note.py").touch()
    _git(root, "add", "-A")
    (root / "cmk" / "gone.py").unlink()


def test_tracked_files_answers_from_the_index(tmp_path: Path) -> None:
    """A file deleted from the worktree is still tracked, which is why `existing` exists."""
    _repo_with_a_deleted_file(tmp_path)
    assert sorted(tracked_files(tmp_path)) == [
        Path("cmk/gone.py"),
        Path("cmk/kept.py"),
        Path("doc/note.py"),
    ]
