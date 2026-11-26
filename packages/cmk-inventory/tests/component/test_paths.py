#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.paths import (
    file_mtime,
    has_archive,
    has_history,
    InventoryPaths,
)


def test_has_archive(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inv_paths.archive_host(HostName("host")).mkdir(parents=True)
    (inv_paths.archive_host(HostName("host")) / "123.json").touch()
    assert has_archive(inv_paths, HostName("host"))


def test_has_no_archive_in_an_empty_directory(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inv_paths.archive_host(HostName("host")).mkdir(parents=True)
    assert not has_archive(inv_paths, HostName("host"))


def test_has_no_archive(tmp_path: Path) -> None:
    assert not has_archive(InventoryPaths(tmp_path), HostName("host"))


@pytest.mark.parametrize(
    "make_directory",
    [
        pytest.param(InventoryPaths.archive_host, id="archive"),
        pytest.param(InventoryPaths.delta_cache_host, id="delta-cache"),
    ],
)
def test_has_history(
    tmp_path: Path, make_directory: Callable[[InventoryPaths, HostName], Path]
) -> None:
    inv_paths = InventoryPaths(tmp_path)
    directory = make_directory(inv_paths, HostName("host"))
    directory.mkdir(parents=True)
    (directory / "123.json").touch()
    assert has_history(inv_paths, HostName("host"))


def test_has_no_history(tmp_path: Path) -> None:
    assert not has_history(InventoryPaths(tmp_path), HostName("host"))


def test_file_mtime(tmp_path: Path) -> None:
    tree_path = InventoryPaths(tmp_path).inventory_tree(HostName("host"))
    tree_path.parent.mkdir(parents=True)
    tree_path.touch()
    os.utime(tree_path, (100, 100))
    assert file_mtime(tree_path) == 100


def test_file_mtime_without_a_file(tmp_path: Path) -> None:
    assert file_mtime(InventoryPaths(tmp_path).inventory_tree(HostName("host"))) is None
