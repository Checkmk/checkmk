#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
from pathlib import Path

import pytest

from cmk.astrein.checker_localization import LocalizationChecker
from cmk.astrein.checker_module_layers import ModuleLayersChecker
from cmk.astrein.checkers import all_checkers
from cmk.astrein.cli import (
    _collect_files,
    _handle_results,
    _run_checkers,
    _select_checkers,
    CheckerResults,
)
from cmk.astrein.framework import ASTVisitorChecker, CheckerError


def test_select_checkers_with_all() -> None:
    checkers = all_checkers()
    selected = _select_checkers("all", checkers)

    assert len(selected) == 2
    assert LocalizationChecker in selected
    assert ModuleLayersChecker in selected


def test_select_checkers_with_specific_checker() -> None:
    checkers = all_checkers()
    selected = _select_checkers("localization", checkers)

    assert len(selected) == 1
    assert selected[0] == LocalizationChecker


def test_select_checkers_with_module_layers() -> None:
    checkers = all_checkers()
    selected = _select_checkers("module-layers", checkers)

    assert len(selected) == 1
    assert selected[0] == ModuleLayersChecker


def test_select_checkers_with_invalid_checker() -> None:
    checkers = all_checkers()

    with pytest.raises(SystemExit, match="Exit: No checkers selected"):
        _select_checkers("invalid-checker", checkers)


def test_collect_files_with_single_python_file(tmp_path: Path) -> None:
    test_file = tmp_path / "test.py"
    test_file.write_text("# test file")

    files = _collect_files([test_file], tmp_path)

    assert len(files) == 1
    assert files[0] == test_file


def test_collect_files_with_directory(tmp_path: Path) -> None:
    (tmp_path / "file1.py").write_text("# file 1")
    (tmp_path / "file2.py").write_text("# file 2")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "file3.py").write_text("# file 3")

    files = _collect_files([tmp_path], tmp_path)

    assert len(files) == 3
    assert tmp_path / "file1.py" in files
    assert tmp_path / "file2.py" in files
    assert subdir / "file3.py" in files


def test_collect_files_excludes_hidden_directories(tmp_path: Path) -> None:
    (tmp_path / "visible.py").write_text("# visible")

    hidden_dir = tmp_path / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "hidden.py").write_text("# hidden")

    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "venv.py").write_text("# venv")

    files = _collect_files([tmp_path], tmp_path)

    assert len(files) == 1
    assert tmp_path / "visible.py" in files
    assert hidden_dir / "hidden.py" not in files
    assert venv_dir / "venv.py" not in files


def test_collect_files_with_nonexistent_path(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist.py"

    with pytest.raises(ValueError, match="Error: Path not found"):
        _collect_files([nonexistent], tmp_path)


def test_collect_files_with_non_python_file(tmp_path: Path) -> None:
    text_file = tmp_path / "readme.txt"
    text_file.write_text("not python")

    with pytest.raises(ValueError, match="Error: Not a Python file"):
        _collect_files([text_file], tmp_path)


def test_collect_files_with_relative_path(tmp_path: Path) -> None:
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.py"
    test_file.write_text("# test")

    files = _collect_files([Path("subdir/test.py")], tmp_path)

    assert len(files) == 1
    assert files[0] == test_file


def test_collect_files_deduplicates_files(tmp_path: Path) -> None:
    test_file = tmp_path / "test.py"
    test_file.write_text("# test")

    files = _collect_files([test_file, test_file], tmp_path)

    assert len(files) == 1
    assert files[0] == test_file


def test_collect_files_sorts_results(tmp_path: Path) -> None:
    (tmp_path / "c.py").write_text("# c")
    (tmp_path / "a.py").write_text("# a")
    (tmp_path / "b.py").write_text("# b")

    files = _collect_files([tmp_path], tmp_path)

    assert len(files) == 3
    assert files[0] == tmp_path / "a.py"
    assert files[1] == tmp_path / "b.py"
    assert files[2] == tmp_path / "c.py"


class HappyChecker(ASTVisitorChecker):
    def checker_id(self) -> str:
        return "happy-checker"

    def visit_Module(self, node: ast.Module) -> None: ...


def test_run_checkers_with_no_errors(tmp_path: Path) -> None:
    test_file = tmp_path / "test.py"
    test_file.write_text("import sys\n")

    results = _run_checkers([test_file], tmp_path, [HappyChecker])

    assert len(results.errors) == 0
    assert results.files_with_errors == 0


def test_run_checkers_with_errors(tmp_path: Path) -> None:
    test_file = tmp_path / "test.py"
    test_file.write_text("# test")

    results = _run_checkers(
        [test_file],
        tmp_path,
        [_make_checker({test_file: [CheckerError("Not good", 1, 0, test_file, "custom-checker")]})],
    )
    assert len(results.errors) == 1
    assert results.files_with_errors == 1
    assert results.errors[0].message == "Not good"


def test_run_checkers_counts_files_with_errors_correctly(tmp_path: Path) -> None:
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    file1.write_text("# test")
    file2.write_text("# test")

    error1 = CheckerError("Error 1", 1, 0, file1, "test")
    error2 = CheckerError("Error 2", 2, 0, file1, "test")
    error3 = CheckerError("Error 3", 1, 0, file2, "test")

    results = _run_checkers(
        [file1, file2], tmp_path, [_make_checker({file1: [error1, error2], file2: [error3]})]
    )

    assert len(results.errors) == 3
    assert results.files_with_errors == 2


def _make_checker(errors_by_file: dict[Path, list[CheckerError]]) -> type[ASTVisitorChecker]:
    class CustomChecker(ASTVisitorChecker):
        def checker_id(self) -> str:
            return "custom-checker"

        def check(self, tree: ast.AST) -> list[CheckerError]:  # noqa: ARG002
            return errors_by_file.get(self.file_path, [])

    return CustomChecker


def test_handle_results_gcc_format_no_errors(capsys: pytest.CaptureFixture[str]) -> None:
    results = CheckerResults(errors=[], files_with_errors=0)

    exit_code = _handle_results(results, "gcc", output_file=None)

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "\n" in captured.out
    assert "" in captured.err


def test_handle_results_gcc_format_with_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    test_file = tmp_path / "test.py"
    error = CheckerError("Test error", 1, 5, test_file, "test-checker")
    results = CheckerResults(errors=[error], files_with_errors=1)

    exit_code = _handle_results(results, "gcc", output_file=None)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "test.py:1:5" in captured.out
    assert "Test error" in captured.out
    assert "Found 1 error(s) across 1 file(s)" in captured.out


def test_handle_results_gcc_format_with_output_file(tmp_path: Path) -> None:
    output_file = tmp_path / "output" / "results.txt"
    test_file = tmp_path / "test.py"
    error = CheckerError("Test error", 1, 5, test_file, "test-checker")
    results = CheckerResults(errors=[error], files_with_errors=1)

    exit_code = _handle_results(results, "gcc", output_file=output_file)

    assert exit_code == 1
    assert output_file.exists()
    content = output_file.read_text()
    assert "test.py:1:5" in content
    assert "Test error" in content
    assert "Found 1 error(s) across 1 file(s)" in content


def test_handle_results_sarif_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    test_file = tmp_path / "test.py"
    error = CheckerError("Test error", 1, 5, test_file, "test-checker")
    results = CheckerResults(errors=[error], files_with_errors=1)

    exit_code = _handle_results(results, "sarif", output_file=None)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out)["version"] == "2.1.0"


def test_handle_results_sarif_format_with_output_file(tmp_path: Path) -> None:
    output_file = tmp_path / "output" / "results.sarif"
    test_file = tmp_path / "test.py"
    error = CheckerError("Test error", 1, 5, test_file, "test-checker")
    results = CheckerResults(errors=[error], files_with_errors=1)

    exit_code = _handle_results(results, "sarif", output_file=output_file)

    assert exit_code == 1
    assert output_file.exists()
    content = output_file.read_text()
    assert json.loads(content)["version"] == "2.1.0"


def test_handle_results_unknown_format(capsys: pytest.CaptureFixture[str]) -> None:
    results = CheckerResults(errors=[], files_with_errors=0)

    exit_code = _handle_results(results, "unknown", output_file=None)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error: Unknown output format: unknown" in captured.err


def test_handle_results_creates_output_directory(tmp_path: Path) -> None:
    output_file = tmp_path / "nested" / "dir" / "output.txt"
    results = CheckerResults(errors=[], files_with_errors=0)

    _handle_results(results, "gcc", output_file=output_file)

    assert output_file.parent.exists()
    assert output_file.exists()


def test_handle_results_multiple_errors_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    errors = [
        CheckerError("Error 1", 1, 0, file1, "test"),
        CheckerError("Error 2", 2, 0, file1, "test"),
        CheckerError("Error 3", 1, 0, file2, "test"),
    ]
    results = CheckerResults(errors=errors, files_with_errors=2)

    exit_code = _handle_results(results, "gcc", output_file=None)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Found 3 error(s) across 2 file(s)" in captured.out
