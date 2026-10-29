# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The files a *-qemu test tier's payload needs in the guest.

A tier's runner (qemu_test, bazel/rules/xcomp/qemu_test.bzl) copies them from
its runfiles into a Stage, with a task.cmd that runs the payload, and hands
the Stage to tier.run(), which copies it into the guest.
"""

import shutil
from collections.abc import Iterable
from pathlib import Path


class Stage:
    """A directory on the host that becomes the payload's directory in the
    guest. Paths in it are relative and use '/'.

    Copies follow symlinks (runfiles are symlinks) and are writable,
    whatever the mode of their source.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def add(self, source: Path, path: str) -> None:
        """The file or directory source, as path."""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, copy_function=shutil.copyfile, dirs_exist_ok=True)
        else:
            shutil.copyfile(source, target)

    def add_files(self, sources: Iterable[Path], directory: str) -> None:
        """Every regular file of sources into directory, by its name."""
        for source in sources:
            if source.is_file():
                self.add(source, f"{directory}/{source.name}")

    def write(self, path: str, text: str) -> None:
        """A guest script (cmd, PowerShell): text with CRLF line ends, which
        cmd.exe's batch parser needs."""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_crlf(text.encode()))

    def to_crlf(self, directory: str, suffixes: Iterable[str]) -> None:
        """The files below directory with one of the suffixes, converted to
        CRLF line ends: the sources are LF in a Linux checkout, the tests
        expect the autocrlf checkout of the legacy Windows nodes."""
        wanted = set(suffixes)
        for path in sorted((self.root / directory).rglob("*")):
            if path.is_file() and path.suffix in wanted:
                path.write_bytes(_crlf(path.read_bytes()))


def read_list(path: Path) -> list[str]:
    """The entries of a list file (test exclusions and the like): one per
    line, surrounding whitespace removed, blank lines and lines starting
    with '#' left out."""
    return [
        entry
        for line in path.read_text().splitlines()
        if (entry := line.strip()) and not entry.startswith("#")
    ]


def _crlf(text: bytes) -> bytes:
    return b"\r\n".join(line.removesuffix(b"\r") for line in text.split(b"\n"))
