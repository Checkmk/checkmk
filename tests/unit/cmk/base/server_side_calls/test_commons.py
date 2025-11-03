#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cmk.server_side_calls_backend._commons import ExecutableFinder


@contextmanager
def _with_file(path: Path) -> Iterator[None]:
    present = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    try:
        yield
    finally:
        if not present:
            path.unlink(missing_ok=True)


def test_executable_finder_local(tmp_path: Path) -> None:
    binary_name = "execthis"
    shipped_file = tmp_path / "shipped" / binary_name
    local_file = tmp_path / "local" / binary_name
    finder = ExecutableFinder(local_file.parent, shipped_file.parent)

    with _with_file(shipped_file):
        assert finder(binary_name, None) == str(shipped_file)
        with _with_file(local_file):
            assert finder(binary_name, None) == str(local_file)
