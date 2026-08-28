#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""List the Python source files the repository-wide coverage number is about.

One list, handed to ``scope`` twice over: it decides which records survive in
the tracefile and which files get a zero-coverage record, so the numerator and
the denominator cannot disagree about what a number covers. ``owned_files`` is
the per-component counterpart, sharing the rule via :mod:`_file_lists`.

Usage:
    source_files.py --repo-root <dir> --source-labels <file> --paths-out <file>
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from tests.qa_metrics.test_coverage._file_lists import source_paths


def main() -> None:
    args = _parse_args()
    paths = source_paths(args.source_labels, args.repo_root)
    if not paths:
        raise SystemExit(
            f"No Python source file survived {args.source_labels} in {args.repo_root}, so there "
            "is nothing to measure."
        )
    args.paths_out.write_text("".join(f"{path}\n" for path in paths))
    print(f"{len(paths)} source file(s) to measure", file=sys.stderr)


@dataclass(frozen=True, kw_only=True)
class _Args:
    repo_root: Path
    source_labels: Path
    paths_out: Path


def _parse_args() -> _Args:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Repository root the paths are relative to. Needed because the "
        "working directory is not the repo under `bazel run`.",
    )
    parser.add_argument(
        "--source-labels",
        required=True,
        type=Path,
        help="Bazel labels of the measured source files, one per line",
    )
    parser.add_argument(
        "--paths-out", required=True, type=Path, help="write the source file paths here"
    )
    args = parser.parse_args()
    return _Args(
        repo_root=args.repo_root, source_labels=args.source_labels, paths_out=args.paths_out
    )


if __name__ == "__main__":
    main()
