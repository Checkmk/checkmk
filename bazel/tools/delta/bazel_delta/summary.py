# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The summary a --delta option prints at the end, and the files a fix changed."""

import sys
from collections.abc import Callable, Mapping, Sequence

from bazel_delta.files import RunCaptured


def echo(message: str = "") -> None:
    sys.stdout.write(f"{message}\n")


def note(message: str) -> None:
    """Prints the message indented, in yellow if stdout is a terminal."""
    echo(f"\033[33m  {message}\033[0m" if sys.stdout.isatty() else f"  {message}")


def summary_lines(title: str, rows: Sequence[tuple[str, int]]) -> list[str]:
    """The title and below it a row per label, with the counts in an aligned column."""
    label_width = max((len(label) for label, _ in rows), default=0)
    count_width = max((len(str(count)) for _, count in rows), default=0)
    return [title] + [f"  {label:<{label_width}} {count:>{count_width}}" for label, count in rows]


def print_summary(title: str, rows: Sequence[tuple[str, int]]) -> None:
    echo()
    for line in summary_lines(title, rows):
        note(line)
    echo()


def dirty_file_hashes(run: RunCaptured, is_file: Callable[[str], bool]) -> dict[str, str]:
    """The git hash of every modified or untracked file of the workspace. Leaves
    out what is no file, such as a submodule or an untracked nested repository."""
    dirty = run(["git", "ls-files", "-z", "--modified", "--others", "--exclude-standard"])
    files = sorted(file for file in set(dirty.split("\0")) if file and is_file(file))
    if not files:
        return {}
    # On stdin, as the files can be too many for one command line
    hashes = run(["git", "hash-object", "--stdin-paths"], stdin="".join(f"{f}\n" for f in files))
    return dict(zip(files, hashes.split(), strict=True))


def changed_files(before: Mapping[str, str], after: Mapping[str, str]) -> list[str]:
    """The files that are new among the dirty files or have another hash than before."""
    return sorted(file for file, file_hash in after.items() if before.get(file) != file_hash)


def print_changed_files(files: Sequence[str], verb: str, if_none: str) -> None:
    if not files:
        note(if_none)
        return
    note(f"{verb} {len(files)} file(s):")
    for file in files:
        note(f"  {file}")
