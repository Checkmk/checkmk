#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The members of a cab, and those no cab may ship of the interpreter.

The interpreter's BUILD file (python_windows_standalone.BUILD.bazel) leaves
them out; this is the check that they stay out.
"""

from collections.abc import Iterable
from pathlib import Path

from cabarchive import CabArchive  # type: ignore[attr-defined, import-not-found, unused-ignore]

# Basename prefixes of the test extension modules and of Tcl/Tk's binaries.
_UNWANTED_BINARY_PREFIXES = ("_test", "_ctypes_test", "_tkinter", "tcl", "tk")
# The DLLs only Tcl loads.
_UNWANTED_BINARIES = {"libtommath.dll", "zlib1.dll"}
# Paths (or path prefixes) from the install root.
_UNWANTED_PATHS = (
    "build-details.json",
    "include/",
    "lib/idlelib/",
    "lib/test/",
    "lib/tkinter/",
    "lib/turtle.py",
    "lib/turtledemo/",
    "libs/",
    "scripts/",
    "tcl/",
)


def members(cab: Path) -> set[str]:
    """The member paths of the cab: lowercase, with forward slashes, from its root."""
    return {m.replace("\\", "/").lstrip("/").lower() for m in CabArchive(cab.read_bytes())}


def unwanted(cab_members: Iterable[str]) -> set[str]:
    """Those of members() that no cab may ship."""
    return {
        m
        for m in cab_members
        if m.endswith(".pdb")
        or m.startswith(_UNWANTED_PATHS)
        or (
            m.endswith((".dll", ".pyd"))
            and (
                (basename := m.rsplit("/", 1)[-1]) in _UNWANTED_BINARIES
                or basename.startswith(_UNWANTED_BINARY_PREFIXES)
            )
        )
    }
