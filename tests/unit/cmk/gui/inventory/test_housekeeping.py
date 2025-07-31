#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
from cmk.gui.inventory._housekeeping import (
    InventoryHousekeeping,
)
from cmk.inventory.config import (
    InvHousekeepingParams,
    InvHousekeepingParamsCombined,
    InvHousekeepingParamsOfHosts,
)
from cmk.inventory.paths import Paths as InventoryPaths
from cmk.inventory.paths import TreePath, TreePathGz


def test_nothing_to_do(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))

    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=100,
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
                for_hosts=[],
                default=None,
                abandoned_file_age=100,
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
                for_hosts=[],
                default=None,
                abandoned_file_age=100,
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
                for_hosts=[],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert archive_host.exists()
    assert delta_cache_host.exists()


@dataclass(frozen=True, kw_only=True)
class _OneArchiveFile:
    inventory_tree: TreePath
    archive_tree_1: TreePath


def _setup_one_archive_file(tmp_path: Path) -> _OneArchiveFile:
    inv_paths = InventoryPaths(tmp_path)
    host_name = HostName("hostname")

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (100, 100))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (100, 100))

    archive_tree_1 = inv_paths.archive_tree(host_name, 1)
    archive_tree_1.legacy.parent.mkdir(parents=True, exist_ok=True)
    archive_tree_1.legacy.touch()

    return _OneArchiveFile(
        inventory_tree=inventory_tree,
        archive_tree_1=archive_tree_1,
    )


def test_one_archive_file_file_age(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path)
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=("file_age", 98),
                    ),
                ],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert files.inventory_tree.exists()
    assert not files.archive_tree_1.exists()


def test_one_archive_file_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path)
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=("number_of_history_entries", 1),
                    ),
                ],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert files.inventory_tree.exists()
    assert files.archive_tree_1.exists()


def test_one_archive_file_file_age_and_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path)
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvHousekeepingParamsCombined(
                                strategy="and",
                                file_age=98,
                                number_of_history_entries=1,
                            ),
                        ),
                    ),
                ],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert files.inventory_tree.exists()
    assert not files.archive_tree_1.exists()


def test_one_archive_file_file_age_or_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path)
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvHousekeepingParamsCombined(
                                strategy="or",
                                file_age=98,
                                number_of_history_entries=1,
                            ),
                        ),
                    ),
                ],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert files.inventory_tree.exists()
    assert not files.archive_tree_1.exists()


@dataclass(frozen=True, kw_only=True)
class _Files:
    inventory_tree: TreePath
    inventory_tree_gz: TreePathGz
    status_data_tree: TreePath
    archive_tree_1: TreePath
    archive_tree_2: TreePath
    archive_tree_3: TreePath
    archive_tree_4: TreePath
    delta_cache_tree_None_1: TreePath
    delta_cache_tree_1_2: TreePath
    delta_cache_tree_2_3: TreePath
    delta_cache_tree_3_4: TreePath
    delta_cache_tree_4_100: TreePath


def _setup_files(tmp_path: Path, host_name: HostName) -> _Files:
    inv_paths = InventoryPaths(tmp_path)

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (100, 100))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (100, 100))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (100, 100))

    archive_tree_1 = inv_paths.archive_tree(host_name, 1)
    archive_tree_2 = inv_paths.archive_tree(host_name, 2)
    archive_tree_3 = inv_paths.archive_tree(host_name, 3)
    archive_tree_4 = inv_paths.archive_tree(host_name, 4)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(host_name, -1, 1)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(host_name, 1, 2)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(host_name, 2, 3)
    delta_cache_tree_3_4 = inv_paths.delta_cache_tree(host_name, 3, 4)
    delta_cache_tree_4_100 = inv_paths.delta_cache_tree(host_name, 4, 100)

    for file_path in [
        archive_tree_1,
        archive_tree_2,
        archive_tree_3,
        archive_tree_4,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_4,
        delta_cache_tree_4_100,
    ]:
        file_path.legacy.parent.mkdir(parents=True, exist_ok=True)
        file_path.legacy.touch()

    return _Files(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
        archive_tree_1=archive_tree_1,
        archive_tree_2=archive_tree_2,
        archive_tree_3=archive_tree_3,
        archive_tree_4=archive_tree_4,
        delta_cache_tree_None_1=delta_cache_tree_None_1,
        delta_cache_tree_1_2=delta_cache_tree_1_2,
        delta_cache_tree_2_3=delta_cache_tree_2_3,
        delta_cache_tree_3_4=delta_cache_tree_3_4,
        delta_cache_tree_4_100=delta_cache_tree_4_100,
    )


def test_file_age(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"))
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=("file_age", 97),
                    )
                ],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree_1.exists()
    assert not files.archive_tree_2.exists()
    assert files.archive_tree_3.exists()
    assert files.archive_tree_4.exists()
    assert not files.delta_cache_tree_None_1.exists()
    assert not files.delta_cache_tree_1_2.exists()
    assert not files.delta_cache_tree_2_3.exists()
    assert files.delta_cache_tree_3_4.exists()
    assert not files.delta_cache_tree_4_100.exists()


def test_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"))
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=("number_of_history_entries", 2),
                    )
                ],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree_1.exists()
    assert files.archive_tree_2.exists()
    assert files.archive_tree_3.exists()
    assert files.archive_tree_4.exists()
    assert not files.delta_cache_tree_None_1.exists()
    assert not files.delta_cache_tree_1_2.exists()
    assert files.delta_cache_tree_2_3.exists()
    assert files.delta_cache_tree_3_4.exists()
    assert not files.delta_cache_tree_4_100.exists()


def test_file_age_and_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"))
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvHousekeepingParamsCombined(
                                strategy="and",
                                file_age=97,
                                number_of_history_entries=2,
                            ),
                        ),
                    ),
                ],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree_1.exists()
    assert files.archive_tree_2.exists()
    assert files.archive_tree_3.exists()
    assert files.archive_tree_4.exists()
    assert not files.delta_cache_tree_None_1.exists()
    assert not files.delta_cache_tree_1_2.exists()
    assert files.delta_cache_tree_2_3.exists()
    assert files.delta_cache_tree_3_4.exists()
    assert not files.delta_cache_tree_4_100.exists()


def test_file_age_or_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"))
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[
                    InvHousekeepingParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvHousekeepingParamsCombined(
                                strategy="or",
                                file_age=97,
                                number_of_history_entries=2,
                            ),
                        ),
                    ),
                ],
                default=None,
                abandoned_file_age=100,
            )
        ),
        host_names=[HostName("hostname")],
        now=100,
    )
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree_1.exists()
    assert not files.archive_tree_2.exists()
    assert files.archive_tree_3.exists()
    assert files.archive_tree_4.exists()
    assert not files.delta_cache_tree_None_1.exists()
    assert not files.delta_cache_tree_1_2.exists()
    assert not files.delta_cache_tree_2_3.exists()
    assert files.delta_cache_tree_3_4.exists()
    assert not files.delta_cache_tree_4_100.exists()


def test_abandoned_file_age(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"))
    unknown_files = _setup_files(tmp_path, HostName("unknown"))
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("known")],
        now=101,
    )
    assert known_files.inventory_tree.exists()
    assert known_files.inventory_tree_gz.legacy.exists()
    assert known_files.status_data_tree.exists()
    assert known_files.archive_tree_1.exists()
    assert known_files.archive_tree_2.exists()
    assert known_files.archive_tree_3.exists()
    assert known_files.archive_tree_4.exists()
    assert known_files.delta_cache_tree_None_1.exists()
    assert known_files.delta_cache_tree_1_2.exists()
    assert known_files.delta_cache_tree_2_3.exists()
    assert known_files.delta_cache_tree_3_4.exists()
    assert known_files.delta_cache_tree_4_100.exists()
    assert not unknown_files.inventory_tree.exists()
    assert not unknown_files.inventory_tree_gz.legacy.exists()
    assert not unknown_files.status_data_tree.exists()
    assert not unknown_files.archive_tree_1.exists()
    assert not unknown_files.archive_tree_2.exists()
    assert not unknown_files.archive_tree_3.exists()
    assert not unknown_files.archive_tree_4.exists()
    assert not unknown_files.archive_tree_4.parent.exists()
    assert not unknown_files.delta_cache_tree_None_1.exists()
    assert not unknown_files.delta_cache_tree_1_2.exists()
    assert not unknown_files.delta_cache_tree_2_3.exists()
    assert not unknown_files.delta_cache_tree_3_4.exists()
    assert not unknown_files.delta_cache_tree_4_100.exists()
    assert not unknown_files.delta_cache_tree_4_100.parent.exists()


def test_abandoned_file_age_keep_history(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"))
    unknown_files = _setup_files(tmp_path, HostName("unknown"))
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("known")],
        now=100,
    )
    assert known_files.inventory_tree.exists()
    assert known_files.inventory_tree_gz.legacy.exists()
    assert known_files.status_data_tree.exists()
    assert known_files.archive_tree_1.exists()
    assert known_files.archive_tree_2.exists()
    assert known_files.archive_tree_3.exists()
    assert known_files.archive_tree_4.exists()
    assert known_files.delta_cache_tree_None_1.exists()
    assert known_files.delta_cache_tree_1_2.exists()
    assert known_files.delta_cache_tree_2_3.exists()
    assert known_files.delta_cache_tree_3_4.exists()
    assert known_files.delta_cache_tree_4_100.exists()
    assert unknown_files.inventory_tree.exists()
    assert unknown_files.inventory_tree_gz.legacy.exists()
    assert unknown_files.status_data_tree.exists()
    assert unknown_files.archive_tree_1.exists()
    assert unknown_files.archive_tree_2.exists()
    assert unknown_files.archive_tree_3.exists()
    assert unknown_files.archive_tree_4.exists()
    assert unknown_files.archive_tree_4.parent.exists()
    assert unknown_files.delta_cache_tree_None_1.exists()
    assert unknown_files.delta_cache_tree_1_2.exists()
    assert unknown_files.delta_cache_tree_2_3.exists()
    assert unknown_files.delta_cache_tree_3_4.exists()
    assert unknown_files.delta_cache_tree_4_100.exists()
    assert unknown_files.delta_cache_tree_4_100.parent.exists()


@dataclass(frozen=True, kw_only=True)
class _FilesNoHistory:
    inventory_tree: TreePath
    inventory_tree_gz: TreePathGz
    status_data_tree: TreePath


def _setup_files_no_history(tmp_path: Path, host_name: HostName) -> _FilesNoHistory:
    inv_paths = InventoryPaths(tmp_path)

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (5, 5))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (5, 5))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (5, 5))

    return _FilesNoHistory(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
    )


def test_abandoned_file_age_no_history(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"))
    unknown_files = _setup_files_no_history(tmp_path, HostName("unknown"))
    InventoryHousekeeping(tmp_path)._run(
        Config(
            inventory_housekeeping=InvHousekeepingParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=96,
            )
        ),
        host_names=[HostName("known")],
        now=100,
    )
    assert known_files.inventory_tree.exists()
    assert known_files.inventory_tree_gz.legacy.exists()
    assert known_files.status_data_tree.exists()
    assert known_files.archive_tree_1.exists()
    assert known_files.archive_tree_2.exists()
    assert known_files.archive_tree_3.exists()
    assert known_files.archive_tree_4.exists()
    assert known_files.delta_cache_tree_None_1.exists()
    assert known_files.delta_cache_tree_1_2.exists()
    assert known_files.delta_cache_tree_2_3.exists()
    assert known_files.delta_cache_tree_3_4.exists()
    assert known_files.delta_cache_tree_4_100.exists()
    assert unknown_files.inventory_tree.exists()
    assert unknown_files.inventory_tree_gz.legacy.exists()
    assert unknown_files.status_data_tree.exists()
