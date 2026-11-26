#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A py_binary with py_stdlib_bytecode() in its data imports the standard library from bytecode."""

import importlib.util
import marshal
import os
import subprocess
from pathlib import Path

# The outputs of :stdlib_bytecode. Bazel's sandboxes link their inputs, so the real path of a .pyc
# tells where it comes from.
_STDLIB_BYTECODE = "/bazel/rules/py_stdlib_bytecode_tests/stdlib_bytecode/"

# The flags of unchecked hash-based bytecode (PEP 552), which Python uses without its source
_UNCHECKED_HASH_BASED = (1).to_bytes(4, "little")


def test_standard_library_module_is_imported_from_the_bytecode() -> None:
    cached = subprocess.run(
        [os.environ["PROBE"]], check=True, stdout=subprocess.PIPE, text=True
    ).stdout.strip()

    pyc = Path(cached).resolve()

    assert _STDLIB_BYTECODE in pyc.as_posix(), f"{cached} is not from py_stdlib_bytecode()"
    data = pyc.read_bytes()
    assert data[:4] == importlib.util.MAGIC_NUMBER, f"{pyc} is for another Python version"
    assert data[4:8] == _UNCHECKED_HASH_BASED, f"{pyc} isn't unchecked hash-based bytecode"
    # Python doesn't check unchecked hash-based bytecode against its source
    source = Path(importlib.util.source_from_cache(cached))
    code = marshal.loads(data[16:])
    assert code == compile(source.read_bytes(), code.co_filename, "exec"), (
        f"{pyc} isn't the bytecode of {source}"
    )
