#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Command-line interface of astrein"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cmk.astrein.checkers import all_checkers
from cmk.astrein.framework import ASTVisitorChecker, CheckerError, run_checkers
from cmk.astrein.sarif import format_sarif


def main() -> int:
    checkers = all_checkers()

    parser = argparse.ArgumentParser(description="Run on python files")
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root path (required for module-layers checker)",
    )
    parser.add_argument(
        "--checker",
        choices=sorted(["all", *checkers.keys()]),
        default="all",
        help="Which checker(s) to run (default: all)",
    )
    parser.add_argument(
        "--format",
        choices=["gcc", "sarif"],
        default="gcc",
        help="Output format: gcc (default) for IDE integration, sarif for CI systems",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (used by Bazel aspect)",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Python files or directories to check (directories are searched recursively)",
    )

    args = parser.parse_args()

    # When running via bazel run, use environment variables to determine workspace
    work_dir = Path(os.environ.get("BUILD_WORKING_DIRECTORY", os.getcwd()))
    workspace_dir = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", work_dir))

    checker_classes = _select_checkers(args.checker, checkers)
    try:
        files_to_check = _collect_files(args.paths, work_dir)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        return 1

    return _handle_results(
        _run_checkers(files_to_check, workspace_dir, checker_classes),
        args.format,
        args.output,
    )


def _select_checkers(
    checker_arg: str, checkers: dict[str, type[ASTVisitorChecker]]
) -> list[type[ASTVisitorChecker]]:
    checker_classes: list[type[ASTVisitorChecker]] = []

    if checker_arg == "all":
        checker_classes.extend(checkers.values())
    elif checker_arg in checkers:
        checker_classes.append(checkers[checker_arg])

    if not checker_classes:
        raise SystemExit("Exit: No checkers selected")

    return checker_classes


def _collect_files(paths: Sequence[Path], workspace_dir: Path) -> list[Path]:
    files_to_check: list[Path] = []

    for path in paths:
        if not path.is_absolute():
            path = workspace_dir / path

        if not path.exists():
            raise ValueError(f"Error: Path not found: {path}")

        if path.is_dir():
            # Recursively find all .py files in directory
            all_py_files = path.rglob("*.py")

            # Filter out files in directories starting with . (like .venv, .git, etc.)
            dir_files = [
                f
                for f in all_py_files
                if not any(part.startswith(".") for part in f.relative_to(path).parts)
            ]

            files_to_check.extend(dir_files)
        elif path.is_file():
            if path.suffix != ".py":
                raise ValueError(f"Error: Not a Python file: {path}")
            files_to_check.append(path)
        else:
            raise ValueError(f"Error: Not a file or directory: {path}")

    files_to_check = sorted(set(files_to_check))
    sys.stderr.write(f"Checking {len(files_to_check)} python files\n")

    return files_to_check


@dataclass
class CheckerResults:
    errors: Sequence[CheckerError]
    files_with_errors: int


def _run_checkers(
    files_to_check: list[Path],
    workspace_dir: Path,
    checker_classes: list[type[ASTVisitorChecker]],
) -> CheckerResults:
    all_errors: list[CheckerError] = []
    files_with_errors = 0

    for file_path in files_to_check:
        errors = run_checkers(file_path, workspace_dir, checker_classes)

        if errors:
            files_with_errors += 1
            all_errors.extend(errors)

    return CheckerResults(all_errors, files_with_errors)


def _handle_results(
    results: CheckerResults,
    output_format: str,
    output_file: Path | None,
) -> int:
    summary = "\n" + (
        (f"Found {len(results.errors)} error(s) across {results.files_with_errors} file(s)\n")
        if results.errors
        else "No errors found\n"
    )

    if output_format == "sarif":
        output = format_sarif(results.errors)
        if output_file is not None:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(output)
        else:
            sys.stdout.write(f"{output}\n")

        if results.errors:
            if output_file is not None:  # Do not mess with sarif output
                sys.stdout.write(f"{summary}\n")
            return 1

    elif output_format == "gcc":
        output = "\n".join(error.format_gcc() for error in results.errors)

        if output_file is not None:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(output + summary)
        else:
            sys.stdout.write(f"{output}\n")

        if results.errors:
            sys.stdout.write(f"{summary}\n")
            return 1
    else:
        sys.stderr.write(f"Error: Unknown output format: {output_format}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
