#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Which files a coverage number is *about*, and how the steps pass them around.

The repository-wide enumeration and the per-component one must answer the first
question identically, or a component's number stops being comparable to the
dashboard's.

A file counts when a Bazel ``py_*`` rule compiles it and no such rule marks it
``testonly``. A non-testonly target may not depend on a testonly one, so the
split follows the build graph rather than a path name.
"""

import subprocess
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path


def read_file_list(path: Path) -> Iterator[Path]:
    """The file's non-blank lines, stripped, as paths."""
    return (Path(stripped) for line in path.read_text().splitlines() if (stripped := line.strip()))


def source_paths(labels_file: Path, repo_root: Path) -> list[Path]:
    """The Python files the coverage denominator counts.

    Bazel's answer intersected with git's: a label list also names generated
    sources -- doctest runners, entry-point shims -- which have no file under
    version control and no line count a denominator could use.
    """
    tracked = set(tracked_files(repo_root))
    return existing(repo_root, sorted(set(_read_source_labels(labels_file)) & tracked))


def tracked_files(repo_root: Path) -> list[Path]:
    """Every tracked path in the repository, relative to ``repo_root``."""
    return [
        Path(line)
        for line in subprocess.run(
            ["git", "-C", str(repo_root), "ls-files"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.splitlines()
    ]


def existing(repo_root: Path, paths: Iterable[Path]) -> list[Path]:
    """The ``paths`` that have a file under ``repo_root``, reporting the rest.

    ``git ls-files`` answers from the index, so a deleted file is still listed.
    Its executable lines are readable only from the source, so it cannot be part
    of a denominator either way, and a dirty checkout should not end a coverage
    run. Reported rather than dropped, since a stale list would otherwise shrink
    the denominator with nothing saying why.
    """
    present: list[Path] = []
    absent: list[Path] = []
    for path in paths:
        if (repo_root / path).is_file():
            present.append(path)
        else:
            absent.append(path)
    if absent:
        print(
            f"Warning: {len(absent)} listed file(s) have no source under {repo_root}, so they "
            f"carry no line count and stay out of the denominator. First "
            f"{min(3, len(absent))}: {', '.join(str(path) for path in absent[:3])}",
            file=sys.stderr,
        )
    return present


def _read_source_labels(path: Path) -> Iterator[Path]:
    """The Bazel source-file labels in ``path``, as repository-relative paths.

    ``//pkg/sub:a/b.py`` names ``pkg/sub/a/b.py``: the colon separates the
    package from the path within it, and only the package part is a directory
    the label spells out.
    """
    for label in read_file_list(path):
        text = str(label)
        if text.startswith("//"):
            package, _, name = text[2:].partition(":")
            yield Path(package) / name
