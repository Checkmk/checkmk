#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Scope an lcov tracefile to a list of source files.

Both halves of one denominator, so one step: records for listed files are kept
and every other record dropped, and listed files that no test loaded get a
zero-coverage record. The same list drives both, so a file cannot count towards
one and not the other.

A coverage run records more than our source -- a test whose dependencies all lie
outside the instrumented dirs gets an empty ``COVERAGE_MANIFEST``, which
coverage.py reads as "no filter". Matching by exact path is what makes this
stronger than ``lcov --extract``, whose unanchored patterns keep those records
and need a second ``lcov --remove`` pass to take them out again.

Usage:
    scope.py --coverage-file <in> --file-list <paths> --output <out>
        --repo-root <dir>
"""

import argparse
import ast
import sys
from collections.abc import Container, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from tests.qa_metrics.test_coverage._file_lists import read_file_list


def main() -> None:
    args = _parse_args()
    if (rejection := _rejection(args.coverage_file, args.output)) is not None:
        print(f"Error: {rejection}", file=sys.stderr)
        sys.exit(1)

    listed = set(read_file_list(args.file_list))
    with args.coverage_file.open(errors="replace") as source, args.output.open("w") as out:
        measured = _write_records(_scoped_records(source, listed, args.repo_root), out)
        added = _write_zero_records(out, sorted(listed - measured), args.repo_root)
    print(
        f"Scoped to {len(listed)} listed file(s) in {args.output}: {len(measured)} measured, "
        f"{added} added at 0%",
        file=sys.stderr,
    )


def _rejection(coverage_file: Path, output: Path) -> str | None:
    """Why this pair of files cannot be processed, or ``None`` if it can."""
    if not coverage_file.exists():
        return f"coverage file not found: {coverage_file}"
    if output.resolve() == coverage_file.resolve():
        return "--output must differ from --coverage-file"
    return None


def _scoped_records(lines: Iterable[str], keep: Container[Path], repo_root: Path) -> Iterator[str]:
    """Yield only the records whose ``SF:`` path is in ``keep`` and that carry data.

    A group holding no ``SF:`` at all is passed through, so no input line is lost.

    Records without a single ``DA:`` line are dropped too: Bazel emits one as the
    baseline for an instrumented file no test imported, and keeping it would
    count the file as measured, leaving its executable lines out of both the
    numerator and the denominator. Dropped, it is reconstructed below instead.
    """
    for record in _records(lines):
        source_file = _source_file(record)
        if source_file is None:
            yield from record  # preamble ahead of the first SF: line
            continue
        path = _repo_relative(source_file, repo_root)
        if path in keep and any(line.startswith("DA:") for line in record):
            yield from _named(record, path)


def _repo_relative(source_file: Path, repo_root: Path) -> Path:
    """``source_file`` as a repository-relative path, where it names one.

    Most runners report workspace-relative paths, but not all: a handful record
    absolute ones, and an absolute path matches nothing in the list, which would
    drop the record and let the file be added back at 0% -- coverage silently
    lost rather than missing. Paths outside the repository, the instrumented
    third-party code among them, are returned unchanged and dropped as before.
    """
    return (
        source_file.relative_to(repo_root) if source_file.is_relative_to(repo_root) else source_file
    )


def _named(record: Iterable[str], path: Path) -> Iterator[str]:
    """``record`` with its ``SF:`` line naming ``path``.

    The output is read by genhtml, which derives each page's name from this path,
    so a record kept under an absolute path would also break the report links.
    """
    for line in record:
        yield f"SF:{path}\n" if line.startswith("SF:") else line


def _write_records(lines: Iterable[str], out: TextIO) -> set[Path]:
    """Write ``lines`` to ``out``, returning the distinct source paths written.

    Paths and not a count, because the caller subtracts them from the list to
    find the files nothing measured.
    """
    written: set[Path] = set()
    for line in lines:
        if (source := _source_path(line)) is not None:
            written.add(source)
        out.write(line)
    return written


def _write_zero_records(out: TextIO, paths: Sequence[Path], repo_root: Path) -> int:
    """Append a zero-coverage record per path, returning how many were written.

    A file with no executable line is left out: it is neither covered nor
    uncovered, and a 0/0 row is a percentage no reader can render.

    Whether a path has a file on disk is settled where the list is produced (see
    :func:`_file_lists.existing`), so a vanished one raises here rather than
    being skipped a second time by a second rule.
    """
    added = 0
    for path in paths:
        executable_lines, functions = _coverage_data((repo_root / path).read_text(errors="replace"))
        if not executable_lines:
            continue
        out.write(f"SF:{path}\n")
        # lcov 2.x function records: FNL declares the function, FNA carries its
        # hit count (always 0 here).
        for index, (lineno, name) in enumerate(functions):
            out.write(f"FNL:{index},{lineno}\n")
            out.write(f"FNA:{index},0,{name}\n")
        out.write(f"FNF:{len(functions)}\nFNH:0\n")
        for lineno in sorted(executable_lines):
            out.write(f"DA:{lineno},0\n")
        out.write(f"LF:{len(executable_lines)}\nLH:0\nend_of_record\n")
        added += 1
    return added


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


def _records(lines: Iterable[str]) -> Iterator[list[str]]:
    """Split a tracefile into records, ``end_of_record`` inclusive.

    A leading group with no ``SF:`` and a trailing group with no
    ``end_of_record`` are yielded too, so no input line is ever lost.
    """
    record: list[str] = []
    for line in lines:
        record.append(line)
        if line.startswith("end_of_record"):
            yield record
            record = []
    if record:
        yield record


def _source_file(record: Sequence[str]) -> Path | None:
    """The record's source path, or ``None`` if it has no ``SF:`` line."""
    return next(
        (source for line in record if (source := _source_path(line)) is not None),
        None,
    )


def _source_path(line: str) -> Path | None:
    """The path an ``SF:`` line names, or ``None`` for any other line."""
    return Path(line[3:].strip()) if line.startswith("SF:") else None


@dataclass(frozen=True, kw_only=True)
class _Args:
    coverage_file: Path
    file_list: Path
    output: Path
    repo_root: Path


def _parse_args() -> _Args:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-file", required=True, type=Path, help="lcov tracefile to read")
    parser.add_argument(
        "--file-list",
        required=True,
        type=Path,
        help="file holding the repository-relative paths to scope to, one per line",
    )
    parser.add_argument("--output", required=True, type=Path, help="lcov tracefile to write")
    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Repository root the listed paths are relative to. Needed to read "
        "the line count of a file no test loaded, and because the working "
        "directory is not the repo under `bazel run`.",
    )
    args = parser.parse_args()
    return _Args(
        coverage_file=args.coverage_file,
        file_list=args.file_list,
        output=args.output,
        repo_root=args.repo_root,
    )


if __name__ == "__main__":
    main()
