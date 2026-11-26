#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Compiles Python sources to bytecode, for py_stdlib_bytecode() in py_stdlib_bytecode.bzl

Takes a file with each source and its .pyc on lines of their own, one after the other.
"""

import py_compile
import sys
from pathlib import Path


def main(params: str) -> None:
    lines = Path(params).read_text().splitlines()
    for source, pyc in zip(lines[::2], lines[1::2], strict=True):
        py_compile.compile(
            source,
            cfile=pyc,
            doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
        )


if __name__ == "__main__":
    main(*sys.argv[1:])
