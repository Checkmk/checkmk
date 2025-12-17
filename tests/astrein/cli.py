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
from pathlib import Path

from tests.astrein.checker_localization import LocalizationChecker
from tests.astrein.framework import ASTVisitorChecker, run_checkers


def main() -> int:
    checkers = _checkers()

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
        "paths",
        nargs="+",
        type=Path,
        help="Python files or directories to check (directories are searched recursively)",
    )

    args = parser.parse_args()

    # When running via bazel run, use BUILD_WORKSPACE_DIRECTORY to resolve paths
    workspace_dir = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", os.getcwd()))

    checker_classes = _select_checkers(args.checker, checkers)
    try:
        files_to_check = _collect_files(args.paths, workspace_dir)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    return _run_checkers(files_to_check, checker_classes)


def _checkers() -> dict[str, type[ASTVisitorChecker]]:
    return {
        "localization": LocalizationChecker,
    }


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
    print(f"Checking {len(files_to_check)} python files", file=sys.stderr)

    return files_to_check


def _run_checkers(
    files_to_check: list[Path],
    checker_classes: list[type[ASTVisitorChecker]],
) -> int:
    total_errors = 0
    files_with_errors = 0
    for file_path in files_to_check:
        errors = run_checkers(file_path, checker_classes)

        if errors:
            files_with_errors += 1

        for error in errors:
            print(error.format_gcc())
            total_errors += 1

    if total_errors > 0:
        print(
            f"\nFound {total_errors} error(s) across {files_with_errors} file(s)",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
