#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Compute the Debian ``Installed-Size`` (in KiB) of a package's data tar archive.

``dpkg-gencontrol`` fills in that control field, but neither ``dpkg-deb --build`` nor
rules_pkg's ``pkg_deb`` does. Without it apt claims that installing the package needs
0 B of disk space.

We mirror the estimate of ``dpkg-gencontrol``: every regular file and symlink counts
with its size rounded up to whole KiB, every other entry (directories, devices, ...)
with 1 KiB. Hard links share their data with the file they point to and add nothing.
Only the tar headers are read, the (potentially huge) archive is never extracted.
"""

import argparse
import sys
import tarfile
from collections.abc import Sequence
from pathlib import Path


def _kib(size: int) -> int:
    return (size + 1023) // 1024


def _entry_kib(member: tarfile.TarInfo) -> int:
    if member.islnk():
        return 0
    if member.isreg():
        return _kib(member.size)
    if member.issym():
        return _kib(len(member.linkname.encode()))
    return 1


def installed_size_kib(archive: Path) -> int:
    # Our own build output, of which only the headers are read. The limits of
    # cmk.ccc.tar_archive are made for untrusted archives and too tight here.
    with tarfile.open(archive) as tar:  # nosemgrep: tarfile-open-read
        return sum(_entry_kib(member) for member in tar)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path, help="the package data tar")
    parser.add_argument("--out", required=True, type=Path, help="file to write the size to")
    args = parser.parse_args(argv)

    args.out.write_text(f"{installed_size_kib(args.archive)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
