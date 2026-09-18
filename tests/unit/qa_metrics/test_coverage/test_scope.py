#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
from pathlib import Path

from tests.qa_metrics.test_coverage.scope import (
    _rejection,
    _scoped_records,
    _write_records,
    _write_zero_records,
)
from tests.qa_metrics.test_coverage.summary import parse_lcov

_REPO = Path("/repo")


def _record(path: str) -> list[str]:
    return [f"SF:{path}\n", "DA:1,1\n", "LF:1\n", "LH:1\n", "end_of_record\n"]


# --- absolute source paths -----------------------------------------------------


def test_keeps_a_listed_record_recorded_under_an_absolute_path() -> None:
    """Some runners report absolute paths; the file is listed relative."""
    lines = _record("/repo/cmk/bi/trees.py")
    kept = list(_scoped_records(lines, {Path("cmk/bi/trees.py")}, _REPO))
    assert kept == _record("cmk/bi/trees.py")


def test_rewrites_the_source_line_of_an_absolute_record() -> None:
    """genhtml names each page from this path, so it must be workspace-relative."""
    kept = list(_scoped_records(_record("/repo/cmk/bi/trees.py"), {Path("cmk/bi/trees.py")}, _REPO))
    assert [line for line in kept if line.startswith("SF:")] == ["SF:cmk/bi/trees.py\n"]


def test_drops_an_absolute_record_outside_the_repository() -> None:
    """Instrumented third-party code, which is not ours to measure."""
    external = _record("/cache/external/pytest/site-packages/_pytest/config.py")
    assert list(_scoped_records(external, {Path("cmk/bi/trees.py")}, _REPO)) == []


def test_drops_an_absolute_record_that_is_not_listed() -> None:
    """Being under the repository is not enough; it must be in the denominator."""
    lines = _record("/repo/cmk/gui/other.py")
    assert list(_scoped_records(lines, {Path("cmk/bi/trees.py")}, _REPO)) == []


def test_does_not_mistake_a_sibling_directory_for_the_repository() -> None:
    """`/repository/...` starts with `/repo` as text but is not under it."""
    lines = _record("/repository/cmk/bi/trees.py")
    assert list(_scoped_records(lines, {Path("cmk/bi/trees.py")}, _REPO)) == []


# --- keeping the listed records ------------------------------------------------


def test_keeps_a_listed_record() -> None:
    lines = _record("cmk/bi/trees.py")
    assert list(_scoped_records(lines, {Path("cmk/bi/trees.py")}, _REPO)) == lines


def test_drops_an_unlisted_record_entirely() -> None:
    assert (
        list(_scoped_records(_record("cmk/gui/other.py"), {Path("cmk/bi/trees.py")}, _REPO)) == []
    )


def test_keeps_only_the_listed_records_of_several() -> None:
    lines = _record("cmk/bi/trees.py") + _record("cmk/gui/other.py") + _record("cmk/bi/search.py")
    kept = list(_scoped_records(lines, {Path("cmk/bi/trees.py"), Path("cmk/bi/search.py")}, _REPO))
    assert [line for line in kept if line.startswith("SF:")] == [
        "SF:cmk/bi/trees.py\n",
        "SF:cmk/bi/search.py\n",
    ]


def test_drops_a_record_that_follows_a_kept_one() -> None:
    lines = _record("cmk/bi/trees.py") + _record("cmk/gui/other.py")
    assert list(_scoped_records(lines, {Path("cmk/bi/trees.py")}, _REPO)) == _record(
        "cmk/bi/trees.py"
    )


def test_matching_is_exact_not_substring() -> None:
    """The reason this exists rather than `lcov --extract`, which matches substrings."""
    leaked = "/home/user/.cache/bazel/somewhere/packages/cmk-bi/trees.py"
    assert list(_scoped_records(_record(leaked), {Path("packages/cmk-bi/trees.py")}, _REPO)) == []


def test_a_suffix_of_a_listed_path_is_not_kept() -> None:
    assert (
        list(_scoped_records(_record("other/cmk/bi/trees.py"), {Path("cmk/bi/trees.py")}, _REPO))
        == []
    )


def test_drops_a_listed_record_that_carries_no_line_data() -> None:
    """Bazel's baseline record for a built-but-never-imported file.

    It must not survive: the file would count as measured, so its executable
    lines would land in neither the numerator nor the denominator. Dropped, it
    is one of the files the zero records reconstruct.
    """
    baseline = [
        "SF:cmk/gui/plugins/bi/utils.py\n",
        "FNF:0\n",
        "FNH:0\n",
        "LH:0\n",
        "LF:0\n",
        "end_of_record\n",
    ]
    assert list(_scoped_records(baseline, {Path("cmk/gui/plugins/bi/utils.py")}, _REPO)) == []


def test_keeps_a_record_whose_lines_are_all_uncovered() -> None:
    """Zero hits is data; zero lines is not."""
    uncovered = ["SF:cmk/bi/trees.py\n", "DA:1,0\n", "LF:1\n", "LH:0\n", "end_of_record\n"]
    assert list(_scoped_records(uncovered, {Path("cmk/bi/trees.py")}, _REPO)) == uncovered


def test_test_name_line_is_kept_with_its_record() -> None:
    """`TN:` introduces a record rather than standing on its own."""
    lines = ["TN:\n", *_record("cmk/bi/trees.py")]
    assert list(_scoped_records(lines, {Path("cmk/bi/trees.py")}, _REPO)) == lines


def test_test_name_line_is_dropped_with_its_record() -> None:
    lines = ["TN:\n", *_record("cmk/gui/other.py")]
    assert list(_scoped_records(lines, {Path("cmk/bi/trees.py")}, _REPO)) == []


def test_a_trailing_group_without_a_source_file_is_passed_through() -> None:
    """No input line is lost to a truncated tracefile."""
    lines = [*_record("cmk/bi/trees.py"), "LF:9\n"]
    assert list(_scoped_records(lines, {Path("cmk/bi/trees.py")}, _REPO)) == lines


def test_an_empty_list_drops_everything() -> None:
    assert list(_scoped_records(_record("cmk/bi/trees.py"), set(), _REPO)) == []


def test_write_records_writes_every_line() -> None:
    out = io.StringIO()
    lines = [*_record("cmk/bi/trees.py"), *_record("cmk/bi/search.py")]
    _write_records(lines, out)
    assert out.getvalue() == "".join(lines)


def test_write_records_collects_the_source_paths() -> None:
    lines = [*_record("cmk/bi/trees.py"), *_record("cmk/bi/search.py")]
    assert _write_records(lines, io.StringIO()) == {
        Path("cmk/bi/trees.py"),
        Path("cmk/bi/search.py"),
    }


def test_write_records_collects_nothing_from_a_tracefile_without_records() -> None:
    assert _write_records(["TN:\n", "LF:9\n"], io.StringIO()) == set()


def test_write_records_reports_each_written_path_once() -> None:
    """A set, because the caller subtracts it from the files it asked for."""
    lines = [*_record("cmk/bi/trees.py"), *_record("cmk/bi/trees.py")]
    assert _write_records(lines, io.StringIO()) == {Path("cmk/bi/trees.py")}


# --- reconstructing the files nothing measured ---------------------------------


def _zero_records(tmp_path: Path, *paths: str) -> str:
    out = io.StringIO()
    _write_zero_records(out, [Path(path) for path in paths], tmp_path)
    return out.getvalue()


def test_a_zero_record_counts_every_line_as_uncovered(tmp_path: Path) -> None:
    (tmp_path / "missing.py").write_text("x = 1\ny = 2\n")
    stats = parse_lcov(_zero_records(tmp_path, "missing.py").splitlines())["missing.py"]
    assert stats.lines == 2
    assert stats.lines_covered == 0


def test_a_zero_record_counts_every_function_as_uncovered(tmp_path: Path) -> None:
    (tmp_path / "missing.py").write_text("def f():\n    pass\n")
    stats = parse_lcov(_zero_records(tmp_path, "missing.py").splitlines())["missing.py"]
    assert stats.functions == 1
    assert stats.functions_covered == 0


def test_a_file_without_executable_lines_gets_no_record(tmp_path: Path) -> None:
    """It is neither covered nor uncovered, and a 0/0 row renders as nothing."""
    (tmp_path / "empty.py").write_text('"""Only a docstring."""\n')
    assert _zero_records(tmp_path, "empty.py") == ""
    assert _write_zero_records(io.StringIO(), [Path("empty.py")], tmp_path) == 0


def test_no_paths_writes_no_record(tmp_path: Path) -> None:
    """Every listed file was measured. coverage.py raises NoDataError on an empty list."""
    assert _write_zero_records(io.StringIO(), [], tmp_path) == 0


def test_the_count_returned_is_the_records_written(tmp_path: Path) -> None:
    for name in ("a.py", "b.py"):
        (tmp_path / name).write_text("x = 1\n")
    assert _write_zero_records(io.StringIO(), [Path("a.py"), Path("b.py")], tmp_path) == 2


def test_only_the_given_paths_get_a_record(tmp_path: Path) -> None:
    """This is what scopes a component report to the component."""
    for name in ("owned.py", "not_owned.py"):
        (tmp_path / name).write_text("x = 1\n")
    written = _zero_records(tmp_path, "owned.py")
    assert "SF:owned.py" in written
    assert "not_owned.py" not in written


def test_a_zero_record_uses_bazels_function_spelling(tmp_path: Path) -> None:
    """Only the text itself pins the form `parse_lcov` reads the hit count from.

    coverage.py and Bazel's combined report agree on FNDA, which is the line that
    carries the count. They disagree on the FN declaration -- coverage.py writes
    `FN:<first>,<last>,<name>`, Bazel `FN:<line>,<name>` -- but nothing in this
    pipeline reads it except genhtml, which accepts both.
    """
    (tmp_path / "missing.py").write_text("def f():\n    pass\n")
    lines = _zero_records(tmp_path, "missing.py").splitlines()
    assert "FNDA:0,f" in lines
    assert "FNF:1" in lines
    assert "FNH:0" in lines
    assert "LF:2" in lines
    assert "LH:0" in lines


# --- refusing to destroy the input --------------------------------------------


def _tracefile(tmp_path: Path, name: str = "coverage.dat") -> Path:
    path = tmp_path / name
    path.write_text("SF:cmk/bi/trees.py\nDA:1,1\nend_of_record\n")
    return path


def test_rejection_reports_an_input_that_is_not_there(tmp_path: Path) -> None:
    assert "not found" in (_rejection(tmp_path / "absent.dat", tmp_path / "out.dat") or "")


def test_rejection_refuses_to_write_back_to_the_input(tmp_path: Path) -> None:
    """Writing back truncates the measurement before it is read."""
    coverage = _tracefile(tmp_path)
    assert _rejection(coverage, coverage) == "--output must differ from --coverage-file"


def test_rejection_sees_through_another_spelling_of_the_input(tmp_path: Path) -> None:
    """The same file named two ways is still the same file."""
    coverage = _tracefile(tmp_path)
    assert _rejection(coverage, tmp_path / "sub" / ".." / "coverage.dat") is not None


def test_rejection_accepts_two_distinct_files(tmp_path: Path) -> None:
    assert _rejection(_tracefile(tmp_path), tmp_path / "scoped.dat") is None
