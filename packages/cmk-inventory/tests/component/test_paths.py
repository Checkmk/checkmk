#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Callable
from operator import attrgetter
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.paths import (
    has_archive,
    has_history,
    has_inventory_tree,
    has_status_data_tree,
    InventoryPaths,
    tree_mtime,
    TreePath,
)

_FILE_KINDS = pytest.mark.parametrize(
    "file_of",
    [
        pytest.param(attrgetter("path"), id="json"),
        pytest.param(attrgetter("legacy"), id="legacy"),
    ],
)


@_FILE_KINDS
def test_has_inventory_tree(tmp_path: Path, file_of: Callable[[TreePath], Path]) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inv_paths.inventory_dir.mkdir(parents=True)
    file_of(inv_paths.inventory_tree(HostName("host"))).touch()
    assert has_inventory_tree(inv_paths, HostName("host"))


def test_has_no_inventory_tree(tmp_path: Path) -> None:
    assert not has_inventory_tree(InventoryPaths(tmp_path), HostName("host"))


@_FILE_KINDS
def test_has_status_data_tree(tmp_path: Path, file_of: Callable[[TreePath], Path]) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inv_paths.status_data_dir.mkdir(parents=True)
    file_of(inv_paths.status_data_tree(HostName("host"))).touch()
    assert has_status_data_tree(inv_paths, HostName("host"))


def test_has_no_status_data_tree(tmp_path: Path) -> None:
    assert not has_status_data_tree(InventoryPaths(tmp_path), HostName("host"))


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


def _touch_tree_files(
    tmp_path: Path, *, json_mtime: int | None, legacy_mtime: int | None
) -> TreePath:
    tree_path = InventoryPaths(tmp_path).inventory_tree(HostName("host"))
    tree_path.path.parent.mkdir(parents=True)
    for file_path, mtime in ((tree_path.path, json_mtime), (tree_path.legacy, legacy_mtime)):
        if mtime is not None:
            file_path.touch()
            os.utime(file_path, (mtime, mtime))
    return tree_path


def test_tree_mtime_prefers_the_json_file(tmp_path: Path) -> None:
    assert tree_mtime(_touch_tree_files(tmp_path, json_mtime=100, legacy_mtime=200)) == 100


def test_tree_mtime_falls_back_to_the_legacy_file(tmp_path: Path) -> None:
    assert tree_mtime(_touch_tree_files(tmp_path, json_mtime=None, legacy_mtime=200)) == 200


def test_tree_mtime_without_a_tree_file(tmp_path: Path) -> None:
    assert tree_mtime(_touch_tree_files(tmp_path, json_mtime=None, legacy_mtime=None)) is None
