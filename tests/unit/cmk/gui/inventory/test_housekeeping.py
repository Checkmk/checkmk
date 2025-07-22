#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
from cmk.gui.inventory._housekeeping import InventoryHousekeeping
from cmk.inventory.config import (
    InvHousekeepingParams,
    InvHousekeepingParamsFallback,
)
from cmk.utils.structured_data import InventoryPaths


def test_nothing_to_do(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert not archive_host.exists()
    assert not delta_cache_host.exists()


def test_only_archive_host(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert archive_host.exists()
    assert not delta_cache_host.exists()


def test_only_delta_cache_host_exists(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))
    delta_cache_host.mkdir(parents=True, exist_ok=True)

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert not archive_host.exists()
    assert delta_cache_host.exists()


def test_both_exist(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))
    delta_cache_host.mkdir(parents=True, exist_ok=True)

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert archive_host.exists()
    assert delta_cache_host.exists()


def test_no_params_one_archive_file(tmp_path: Path) -> None:
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
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert archive_tree_1.exists()
    assert not archive_tree_2.exists()
    assert not archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert not delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_params_one_archive_file(tmp_path: Path) -> None:
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
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(file_age=97, number_of_history_entries=1),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert not archive_tree_2.exists()
    assert not archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert not delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_no_params_and_all(tmp_path: Path) -> None:
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
        archive_tree_3,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert delta_cache_tree_None_1.exists()
    assert delta_cache_tree_1_2.exists()
    assert delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_no_params_and_only_archive_files(tmp_path: Path) -> None:
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
        archive_tree_3,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert not delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_no_params_and_only_delta_caches(tmp_path: Path) -> None:
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
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert not archive_tree_2.exists()
    assert not archive_tree_3.exists()
    assert delta_cache_tree_None_1.exists()
    assert delta_cache_tree_1_2.exists()
    assert delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_file_age_and_all(tmp_path: Path) -> None:
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
        archive_tree_3,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(file_age=97, number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_file_age_and_only_archive_files(tmp_path: Path) -> None:
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
        archive_tree_3,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(file_age=97, number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert not delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_file_age_and_only_delta_caches(tmp_path: Path) -> None:
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
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(file_age=97, number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert not archive_tree_2.exists()
    assert not archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_number_of_history_entries_and_all(tmp_path: Path) -> None:
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
        archive_tree_3,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=1),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_number_of_history_entries_and_only_archive_files(tmp_path: Path) -> None:
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
        archive_tree_3,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=1),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert archive_tree_2.exists()
    assert archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert not delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_number_of_history_entries_and_only_delta_caches(tmp_path: Path) -> None:
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
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_100,
    ]:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(number_of_history_entries=1),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert not archive_tree_2.exists()
    assert not archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()


def test_unhandled_file_paths(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inventory_tree = inv_paths.inventory_tree(HostName("unknown"))
    archive_tree_1 = inv_paths.archive_tree(HostName("unknown"), 1)
    archive_tree_2 = inv_paths.archive_tree(HostName("unknown"), 2)
    archive_tree_3 = inv_paths.archive_tree(HostName("unknown"), 3)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(HostName("unknown"), -1, 1)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(HostName("unknown"), 1, 2)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(HostName("unknown"), 2, 3)
    delta_cache_tree_3_100 = inv_paths.delta_cache_tree(HostName("unknown"), 3, 100)
    for file_path in [
        inventory_tree,
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
    os.utime(inventory_tree.legacy, (100, 100))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                of_hosts=[],
                fallback=InvHousekeepingParamsFallback(file_age=97, number_of_history_entries=100),
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert not inventory_tree.exists()
    assert not archive_tree_1.exists()
    assert not archive_tree_2.exists()
    assert not archive_tree_3.exists()
    assert not delta_cache_tree_None_1.exists()
    assert not delta_cache_tree_1_2.exists()
    assert not delta_cache_tree_2_3.exists()
    assert not delta_cache_tree_3_100.exists()
