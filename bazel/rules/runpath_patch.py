#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared helpers for depth-relative $ORIGIN RUNPATH patching of ELF files."""

import os

ELF_MAGIC = b"\x7fELF"


def is_elf(header: bytes) -> bool:
    """Return True if the given leading bytes start with the ELF magic."""
    return header[:4] == ELF_MAGIC


def depth_relative_rpath(base_rpath: str, rel_dir: str) -> str:
    """Compute the RUNPATH for a file nested in ``rel_dir`` below the tree root.

    ``rel_dir`` is the file's directory relative to the tree root ("." for the
    root). Files deeper than the top level get extra ".." segments appended so
    that the $ORIGIN-relative ``base_rpath`` keeps pointing at the same target.
    """
    depth = len(rel_dir.split(os.sep)) if rel_dir != "." else 0
    extra_ups = "/".join([".."] * (depth - 1)) if depth > 1 else ""
    return f"{base_rpath}/{extra_ups}" if extra_ups else base_rpath
