#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Patches ELF files in a directory tree with depth-relative $ORIGIN rpaths."""

import os
import shutil
import subprocess
import sys


def _is_elf(filepath: str) -> bool:
    try:
        with open(filepath, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def _patch_elf_files(directory: str, patchelf: str, base_rpath: str) -> None:
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.islink(filepath):
                continue
            if not _is_elf(filepath):
                continue
            rel_dir = os.path.relpath(dirpath, directory)
            depth = len(rel_dir.split(os.sep)) if rel_dir != "." else 0
            extra_ups = "/".join([".."] * (depth - 1)) if depth > 1 else ""
            rpath = f"{base_rpath}/{extra_ups}" if extra_ups else base_rpath
            subprocess.run([patchelf, "--set-rpath", rpath, filepath], check=True)


def main() -> None:
    src_dir, out_dir, patchelf, base_rpath = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    if src_dir != out_dir:
        shutil.copytree(src_dir, out_dir, copy_function=shutil.copyfile, dirs_exist_ok=True)
    _patch_elf_files(out_dir, patchelf, base_rpath)


if __name__ == "__main__":
    main()
