#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from cmk.ccc.hostaddress import HostName

from cmk.utils.structured_data import InventoryPaths

from cmk.gui.config import Config
from cmk.gui.inventory._housekeeping import InventoryHousekeeping


def test_nothing_to_do(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))

    InventoryHousekeeping(tmp_path)(Config())
    assert not archive_host.exists()
    assert not delta_cache_host.exists()


def test_only_archive_host(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))

    InventoryHousekeeping(tmp_path)(Config())
    assert archive_host.exists()
    assert not delta_cache_host.exists()


def test_only_delta_cache_host_exists(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))
    delta_cache_host.mkdir(parents=True, exist_ok=True)

    InventoryHousekeeping(tmp_path)(Config())
    assert not archive_host.exists()
    assert delta_cache_host.exists()


def test_both_exist(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))
    delta_cache_host.mkdir(parents=True, exist_ok=True)

    InventoryHousekeeping(tmp_path)(Config())
    assert archive_host.exists()
    assert delta_cache_host.exists()


def test_rm_delta_cache_host(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname1"))
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname2"))
    delta_cache_host.mkdir(parents=True, exist_ok=True)

    InventoryHousekeeping(tmp_path)(Config())
    assert archive_host.exists()
    assert not delta_cache_host.exists()


def test_no_inventory_tree(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inventory_tree = inv_paths.inventory_tree(HostName("hostname"))
    archive_tree_1 = inv_paths.archive_tree(HostName("hostname"), 1)
    archive_tree_2 = inv_paths.archive_tree(HostName("hostname"), 2)
    archive_tree_3 = inv_paths.archive_tree(HostName("hostname"), 3)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(HostName("hostname"), -1, 1)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(HostName("hostname"), 1, 2)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(HostName("hostname"), 2, 3)
    delta_cache_tree_3_100 = inv_paths.delta_cache_tree(HostName("hostname"), 3, 100)
    for file_path in [
        archive_tree_1,
        archive_tree_2,
        archive_tree_3,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()

    InventoryHousekeeping(tmp_path)(Config())
    assert not inventory_tree.exists()
    assert archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert delta_cache_tree_None_1.exists()
    assert delta_cache_tree_1_2.exists()
    assert delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_no_archive_tree_1(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inventory_tree = inv_paths.inventory_tree(HostName("hostname"))
    archive_tree_1 = inv_paths.archive_tree(HostName("hostname"), 1)
    archive_tree_2 = inv_paths.archive_tree(HostName("hostname"), 2)
    archive_tree_3 = inv_paths.archive_tree(HostName("hostname"), 3)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(HostName("hostname"), -1, 1)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(HostName("hostname"), 1, 2)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(HostName("hostname"), 2, 3)
    delta_cache_tree_3_100 = inv_paths.delta_cache_tree(HostName("hostname"), 3, 100)
    for file_path in [
        inventory_tree,
        archive_tree_2,
        archive_tree_3,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)(Config())
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert delta_cache_tree_2_3.exists()
    assert delta_cache_tree_3_100.exists()


def test_no_archive_tree_2(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inventory_tree = inv_paths.inventory_tree(HostName("hostname"))
    archive_tree_1 = inv_paths.archive_tree(HostName("hostname"), 1)
    archive_tree_2 = inv_paths.archive_tree(HostName("hostname"), 2)
    archive_tree_3 = inv_paths.archive_tree(HostName("hostname"), 3)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(HostName("hostname"), -1, 1)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(HostName("hostname"), 1, 2)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(HostName("hostname"), 2, 3)
    delta_cache_tree_3_100 = inv_paths.delta_cache_tree(HostName("hostname"), 3, 100)
    for file_path in [
        inventory_tree,
        archive_tree_1,
        archive_tree_3,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)(Config())
    assert inventory_tree.exists()
    assert archive_tree_1.exists()
    assert not archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert not delta_cache_tree_2_3.exists()
    assert delta_cache_tree_3_100.exists()


def test_no_archive_tree_3(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inventory_tree = inv_paths.inventory_tree(HostName("hostname"))
    archive_tree_1 = inv_paths.archive_tree(HostName("hostname"), 1)
    archive_tree_2 = inv_paths.archive_tree(HostName("hostname"), 2)
    archive_tree_3 = inv_paths.archive_tree(HostName("hostname"), 3)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(HostName("hostname"), -1, 1)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(HostName("hostname"), 1, 2)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(HostName("hostname"), 2, 3)
    delta_cache_tree_3_100 = inv_paths.delta_cache_tree(HostName("hostname"), 3, 100)
    for file_path in [
        inventory_tree,
        archive_tree_1,
        archive_tree_2,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)(Config())
    assert inventory_tree.exists()
    assert archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert not archive_tree_3.exists()
    assert delta_cache_tree_None_1.exists()
    assert delta_cache_tree_1_2.exists()
    assert not delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()
