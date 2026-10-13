#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.qa_metrics.test_coverage.owned_files import (
    _bazel_package,
    _nothing_to_measure,
    _package_patterns,
)


def test_nothing_to_measure_of_a_component_owning_nothing() -> None:
    message = _nothing_to_measure("ghost", [])
    assert "owns no Python file" in message


def test_nothing_to_measure_of_a_component_owning_only_test_support() -> None:
    """Owning tests but no sources is a different problem, and must read as one."""
    message = _nothing_to_measure("tests_only", [Path("cmk/tests/test_a.py")])
    assert "owns 1 Python file(s)" in message
    assert "testonly to Bazel" in message


def test_bazel_package_is_the_nearest_ancestor_with_a_build_file(tmp_path: Path) -> None:
    (tmp_path / "cmk/gui/wato").mkdir(parents=True)
    (tmp_path / "cmk/BUILD").touch()
    (tmp_path / "cmk/gui/wato/BUILD").touch()
    assert _bazel_package(Path("cmk/gui/wato/page.py"), tmp_path) == "//cmk/gui/wato"


def test_bazel_package_walks_up_past_directories_without_a_build_file(tmp_path: Path) -> None:
    (tmp_path / "cmk/gui/wato").mkdir(parents=True)
    (tmp_path / "cmk/BUILD").touch()
    assert _bazel_package(Path("cmk/gui/wato/page.py"), tmp_path) == "//cmk"


def test_bazel_package_accepts_build_bazel(tmp_path: Path) -> None:
    (tmp_path / "packages/cmk-crypto").mkdir(parents=True)
    (tmp_path / "packages/cmk-crypto/BUILD.bazel").touch()
    assert _bazel_package(Path("packages/cmk-crypto/keys.py"), tmp_path) == "//packages/cmk-crypto"


def test_bazel_package_of_root_package(tmp_path: Path) -> None:
    (tmp_path / "BUILD").touch()
    assert _bazel_package(Path("setup.py"), tmp_path) == "//"


def test_bazel_package_is_none_without_any_build_file(tmp_path: Path) -> None:
    (tmp_path / "cmk/gui").mkdir(parents=True)
    assert _bazel_package(Path("cmk/gui/page.py"), tmp_path) is None


def test_bazel_package_ignores_a_build_directory(tmp_path: Path) -> None:
    """Only a BUILD *file* declares a package."""
    (tmp_path / "cmk/BUILD").mkdir(parents=True)
    assert _bazel_package(Path("cmk/page.py"), tmp_path) is None


def test_package_patterns_emits_one_pattern_per_package(tmp_path: Path) -> None:
    (tmp_path / "cmk/bi").mkdir(parents=True)
    (tmp_path / "cmk/bi/BUILD").touch()
    assert _package_patterns([Path("cmk/bi/trees.py")], tmp_path) == "//cmk/bi:*\n"


def test_package_patterns_collapses_files_sharing_a_package(tmp_path: Path) -> None:
    """Package granularity is the point: the query needs each package once."""
    (tmp_path / "cmk/bi/sub").mkdir(parents=True)
    (tmp_path / "cmk/bi/BUILD").touch()
    paths = [Path("cmk/bi/trees.py"), Path("cmk/bi/search.py"), Path("cmk/bi/sub/nested.py")]
    assert _package_patterns(paths, tmp_path) == "//cmk/bi:*\n"


def test_package_patterns_are_sorted(tmp_path: Path) -> None:
    for package in ("cmk/gui", "cmk/bi"):
        (tmp_path / package).mkdir(parents=True)
        (tmp_path / package / "BUILD").touch()
    assert _package_patterns([Path("cmk/gui/page.py"), Path("cmk/bi/trees.py")], tmp_path) == (
        "//cmk/bi:*\n//cmk/gui:*\n"
    )


def test_package_patterns_omits_a_path_in_no_package(tmp_path: Path) -> None:
    (tmp_path / "cmk/bi").mkdir(parents=True)
    (tmp_path / "cmk/bi/BUILD").touch()
    (tmp_path / "loose").mkdir()
    assert (
        _package_patterns([Path("cmk/bi/trees.py"), Path("loose/orphan.py")], tmp_path)
        == "//cmk/bi:*\n"
    )


def test_package_patterns_reports_a_path_in_no_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Silently dropping it would read as coverage of a file no test can reach."""
    (tmp_path / "loose").mkdir()
    assert _package_patterns([Path("loose/orphan.py")], tmp_path) == ""
    assert "loose/orphan.py" in capsys.readouterr().err


def test_package_patterns_of_no_paths_is_empty(tmp_path: Path) -> None:
    assert _package_patterns([], tmp_path) == ""
