#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Append zero-coverage lcov entries for repo source files absent from the report.

Files that are never imported during a test run produce no coverage data at all,
making them invisible in the report.  This script finds every .py file under the
given source directories, compares against the paths already in the lcov coverage
file, and appends zero-coverage entries for each missing file so they show up as 0%.

Must be run from the repository root.

Usage:
    add_missing_coverage.py --coverage-file <path> <source-dir> [...]
"""

import argparse
import ast
import subprocess
import sys
from pathlib import Path


def files_in_coverage_file(coverage_file: Path) -> set[str]:
    """Return the set of source file paths already present in the lcov coverage file."""
    return {
        line[3:]
        for line in coverage_file.read_text(errors="replace").splitlines()
        if line.startswith("SF:")
    }


def _tracked_py_files(source_dirs: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"] + source_dirs,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(p for p in result.stdout.splitlines() if p.endswith(".py"))


def _coverage_data(source: str) -> tuple[set[int], list[tuple[int, str]]]:
    """Parse source and return executable lines and functions."""
    tree = ast.parse(source)

    lines: set[int] = set()
    functions: list[tuple[int, str]] = []

    def collect_functions(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                collect_functions(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{child.name}"
                functions.append((child.lineno, name))
                collect_functions(child, f"{name}.<locals>.")
            else:
                collect_functions(child, prefix)

    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue
            lines.add(node.lineno)
            for decorator in getattr(node, "decorator_list", []):
                lines.add(decorator.lineno)

    collect_functions(tree, "")
    return lines, functions


def append_zero_entries(coverage_file: Path, source_dirs: list[str]) -> int:
    already_present = files_in_coverage_file(coverage_file)
    candidates = 0
    added = 0

    with coverage_file.open("a") as out:
        for rel in _tracked_py_files(source_dirs):
            if "tests" in Path(rel).parts:
                continue
            candidates += 1
            if rel in already_present:
                continue
            source = Path(rel).read_text(errors="replace")
            executable_lines, functions = _coverage_data(source)
            if not executable_lines:
                continue
            out.write(f"SF:{rel}\n")
            for lineno, name in functions:
                out.write(f"FN:{lineno},{name}\n")
            for _, name in functions:
                out.write(f"FNDA:0,{name}\n")
            out.write(f"FNF:{len(functions)}\nFNH:0\n")
            for lineno in sorted(executable_lines):
                out.write(f"DA:{lineno},0\n")
            out.write(f"LF:{len(executable_lines)}\nLH:0\nend_of_record\n")
            added += 1

    print(
        f"Already in coverage file: {len(already_present)}, candidates: {candidates}, "
        f"added {added} zero-coverage entries to {coverage_file}",
        file=sys.stderr,
    )
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage-file", required=True, type=Path, help="lcov coverage file to append to"
    )
    parser.add_argument("dirs", nargs="+", help="source directories relative to repo root")
    args = parser.parse_args()

    if not args.coverage_file.exists():
        print(f"Error: coverage file not found: {args.coverage_file}", file=sys.stderr)
        sys.exit(1)

    append_zero_entries(args.coverage_file, args.dirs)


if __name__ == "__main__":
    main()
