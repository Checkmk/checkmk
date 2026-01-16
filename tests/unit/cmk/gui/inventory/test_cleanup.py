#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
from cmk.gui.inventory._cleanup import (
    InventoryCleanup,
)
from cmk.inventory.config import (
    InvCleanupParams,
    InvCleanupParamsCombined,
    InvCleanupParamsOfHosts,
)
from cmk.inventory.paths import Paths as InventoryPaths
from cmk.inventory.paths import TreePath, TreePathGz


def test_nothing_to_do(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    archive_host = inv_paths.archive_host(HostName("hostname"))
    delta_cache_host = inv_paths.delta_cache_host(HostName("hostname"))

    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
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

    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
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

    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
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

    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
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
    inventory_tree_gz: TreePathGz
    status_data_tree: TreePath
    archive_tree: TreePath


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
    delta_cache_tree_4_ts: TreePath


@dataclass(frozen=True, kw_only=True)
class _FilesNoHistory:
    inventory_tree: TreePath
    inventory_tree_gz: TreePathGz
    status_data_tree: TreePath


def _setup_one_archive_file(tmp_path: Path, *, timestamp: int) -> _OneArchiveFile:
    inv_paths = InventoryPaths(tmp_path)
    host_name = HostName("hostname")

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (timestamp, timestamp))

    archive_tree = inv_paths.archive_tree(host_name, timestamp - 1)
    archive_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    archive_tree.legacy.touch()

    return _OneArchiveFile(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
        archive_tree=archive_tree,
    )


def test_one_archive(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert files.archive_tree.legacy.exists()


def test_one_archive_file_file_age(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=("file_age", 2),
                    ),
                ],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert not files.archive_tree.legacy.exists()


def test_one_archive_file_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=("number_of_history_entries", 1),
                    ),
                ],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert files.archive_tree.legacy.exists()


def test_one_archive_file_file_age_and_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=2,
                                number_of_history_entries=1,
                            ),
                        ),
                    ),
                ],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert not files.archive_tree.legacy.exists()


def test_one_archive_file_file_age_or_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_one_archive_file(tmp_path, timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="or",
                                file_age=2,
                                number_of_history_entries=1,
                            ),
                        ),
                    ),
                ],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert not files.archive_tree.legacy.exists()


def _setup_files(tmp_path: Path, host_name: HostName, *, timestamp: int) -> _Files:
    inv_paths = InventoryPaths(tmp_path)

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (timestamp, timestamp))

    archive_tree_1 = inv_paths.archive_tree(host_name, timestamp - 4)
    archive_tree_2 = inv_paths.archive_tree(host_name, timestamp - 3)
    archive_tree_3 = inv_paths.archive_tree(host_name, timestamp - 2)
    archive_tree_4 = inv_paths.archive_tree(host_name, timestamp - 1)
    delta_cache_tree_None_1 = inv_paths.delta_cache_tree(host_name, timestamp - 5, timestamp - 4)
    delta_cache_tree_1_2 = inv_paths.delta_cache_tree(host_name, timestamp - 4, timestamp - 3)
    delta_cache_tree_2_3 = inv_paths.delta_cache_tree(host_name, timestamp - 3, timestamp - 2)
    delta_cache_tree_3_4 = inv_paths.delta_cache_tree(host_name, timestamp - 2, timestamp - 1)
    delta_cache_tree_4_ts = inv_paths.delta_cache_tree(host_name, timestamp - 1, timestamp)

    for file_path in [
        archive_tree_1,
        archive_tree_2,
        archive_tree_3,
        archive_tree_4,
        delta_cache_tree_None_1,
        delta_cache_tree_1_2,
        delta_cache_tree_2_3,
        delta_cache_tree_3_4,
        delta_cache_tree_4_ts,
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
        delta_cache_tree_4_ts=delta_cache_tree_4_ts,
    )


def test_file_age(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=("file_age", 3),
                    )
                ],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert not files.archive_tree_1.legacy.exists()
    assert not files.archive_tree_2.legacy.exists()
    assert files.archive_tree_3.legacy.exists()
    assert files.archive_tree_4.legacy.exists()
    assert not files.delta_cache_tree_None_1.legacy.exists()
    assert not files.delta_cache_tree_1_2.legacy.exists()
    assert not files.delta_cache_tree_2_3.legacy.exists()
    assert files.delta_cache_tree_3_4.legacy.exists()
    assert not files.delta_cache_tree_4_ts.legacy.exists()


def test_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=("number_of_history_entries", 2),
                    )
                ],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert not files.archive_tree_1.legacy.exists()
    assert files.archive_tree_2.legacy.exists()
    assert files.archive_tree_3.legacy.exists()
    assert files.archive_tree_4.legacy.exists()
    assert not files.delta_cache_tree_None_1.legacy.exists()
    assert not files.delta_cache_tree_1_2.legacy.exists()
    assert files.delta_cache_tree_2_3.legacy.exists()
    assert files.delta_cache_tree_3_4.legacy.exists()
    assert not files.delta_cache_tree_4_ts.legacy.exists()


def test_file_age_and_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="and",
                                file_age=3,
                                number_of_history_entries=2,
                            ),
                        ),
                    ),
                ],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert not files.archive_tree_1.legacy.exists()
    assert files.archive_tree_2.legacy.exists()
    assert files.archive_tree_3.legacy.exists()
    assert files.archive_tree_4.legacy.exists()
    assert not files.delta_cache_tree_None_1.legacy.exists()
    assert not files.delta_cache_tree_1_2.legacy.exists()
    assert files.delta_cache_tree_2_3.legacy.exists()
    assert files.delta_cache_tree_3_4.legacy.exists()
    assert not files.delta_cache_tree_4_ts.legacy.exists()


def test_file_age_or_number_of_history_entries(tmp_path: Path) -> None:
    files = _setup_files(tmp_path, HostName("hostname"), timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[
                    InvCleanupParamsOfHosts(
                        regex_or_explicit=["hostname"],
                        parameters=(
                            "combined",
                            InvCleanupParamsCombined(
                                strategy="or",
                                file_age=3,
                                number_of_history_entries=2,
                            ),
                        ),
                    ),
                ],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("hostname")],
        now=101,
    )
    assert files.inventory_tree.legacy.exists()
    assert files.inventory_tree_gz.legacy.exists()
    assert files.status_data_tree.legacy.exists()
    assert not files.archive_tree_1.legacy.exists()
    assert not files.archive_tree_2.legacy.exists()
    assert files.archive_tree_3.legacy.exists()
    assert files.archive_tree_4.legacy.exists()
    assert not files.delta_cache_tree_None_1.legacy.exists()
    assert not files.delta_cache_tree_1_2.legacy.exists()
    assert not files.delta_cache_tree_2_3.legacy.exists()
    assert files.delta_cache_tree_3_4.legacy.exists()
    assert not files.delta_cache_tree_4_ts.legacy.exists()


def test_abandoned_file_age_youngest_too_old(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _setup_files(tmp_path, HostName("unknown"), timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=1,
            )
        ),
        host_names=[HostName("known")],
        now=101,
    )
    assert known_files.inventory_tree.legacy.exists()
    assert known_files.inventory_tree_gz.legacy.exists()
    assert known_files.status_data_tree.legacy.exists()
    assert known_files.archive_tree_1.legacy.exists()
    assert known_files.archive_tree_2.legacy.exists()
    assert known_files.archive_tree_3.legacy.exists()
    assert known_files.archive_tree_4.legacy.exists()
    assert known_files.delta_cache_tree_None_1.legacy.exists()
    assert known_files.delta_cache_tree_1_2.legacy.exists()
    assert known_files.delta_cache_tree_2_3.legacy.exists()
    assert known_files.delta_cache_tree_3_4.legacy.exists()
    assert known_files.delta_cache_tree_4_ts.legacy.exists()
    assert not unknown_files.inventory_tree.legacy.exists()
    assert not unknown_files.inventory_tree_gz.legacy.exists()
    assert not unknown_files.status_data_tree.legacy.exists()
    assert not unknown_files.archive_tree_1.legacy.exists()
    assert not unknown_files.archive_tree_2.legacy.exists()
    assert not unknown_files.archive_tree_3.legacy.exists()
    assert not unknown_files.archive_tree_4.legacy.exists()
    assert not unknown_files.archive_tree_4.legacy.parent.exists()
    assert not unknown_files.delta_cache_tree_None_1.legacy.exists()
    assert not unknown_files.delta_cache_tree_1_2.legacy.exists()
    assert not unknown_files.delta_cache_tree_2_3.legacy.exists()
    assert not unknown_files.delta_cache_tree_3_4.legacy.exists()
    assert not unknown_files.delta_cache_tree_4_ts.legacy.exists()
    assert not unknown_files.delta_cache_tree_4_ts.legacy.parent.exists()


def test_abandoned_file_age_youngest_not_too_old(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _setup_files(tmp_path, HostName("unknown"), timestamp=100)
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=2,
            )
        ),
        host_names=[HostName("known")],
        now=101,
    )
    assert known_files.inventory_tree.legacy.exists()
    assert known_files.inventory_tree_gz.legacy.exists()
    assert known_files.status_data_tree.legacy.exists()
    assert known_files.archive_tree_1.legacy.exists()
    assert known_files.archive_tree_2.legacy.exists()
    assert known_files.archive_tree_3.legacy.exists()
    assert known_files.archive_tree_4.legacy.exists()
    assert known_files.delta_cache_tree_None_1.legacy.exists()
    assert known_files.delta_cache_tree_1_2.legacy.exists()
    assert known_files.delta_cache_tree_2_3.legacy.exists()
    assert known_files.delta_cache_tree_3_4.legacy.exists()
    assert known_files.delta_cache_tree_4_ts.legacy.exists()
    assert unknown_files.inventory_tree.legacy.exists()
    assert unknown_files.inventory_tree_gz.legacy.exists()
    assert unknown_files.status_data_tree.legacy.exists()
    assert unknown_files.archive_tree_1.legacy.exists()
    assert unknown_files.archive_tree_2.legacy.exists()
    assert unknown_files.archive_tree_3.legacy.exists()
    assert unknown_files.archive_tree_4.legacy.exists()
    assert unknown_files.delta_cache_tree_None_1.legacy.exists()
    assert unknown_files.delta_cache_tree_1_2.legacy.exists()
    assert unknown_files.delta_cache_tree_2_3.legacy.exists()
    assert unknown_files.delta_cache_tree_3_4.legacy.exists()
    assert unknown_files.delta_cache_tree_4_ts.legacy.exists()


def _setup_files_no_history(
    tmp_path: Path, host_name: HostName, *, timestamp: int
) -> _FilesNoHistory:
    inv_paths = InventoryPaths(tmp_path)

    inventory_tree = inv_paths.inventory_tree(host_name)
    inventory_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.legacy.touch()
    os.utime(inventory_tree.legacy, (timestamp, timestamp))

    inventory_tree_gz = inv_paths.inventory_tree_gz(host_name)
    inventory_tree_gz.legacy.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.legacy.touch()
    os.utime(inventory_tree_gz.legacy, (timestamp, timestamp))

    status_data_tree = inv_paths.status_data_tree(host_name)
    status_data_tree.legacy.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.legacy.touch()
    os.utime(status_data_tree.legacy, (timestamp, timestamp))

    return _FilesNoHistory(
        inventory_tree=inventory_tree,
        inventory_tree_gz=inventory_tree_gz,
        status_data_tree=status_data_tree,
    )


def test_abandoned_file_age_remaining_files_too_old(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _setup_files(tmp_path, HostName("unknown"), timestamp=100)
    unknown_files_no_history = _setup_files_no_history(
        tmp_path, HostName("unknown-no-history"), timestamp=99
    )
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=2,
            )
        ),
        host_names=[HostName("known")],
        now=101,
    )
    assert known_files.inventory_tree.legacy.exists()
    assert known_files.inventory_tree_gz.legacy.exists()
    assert known_files.status_data_tree.legacy.exists()
    assert known_files.archive_tree_1.legacy.exists()
    assert known_files.archive_tree_2.legacy.exists()
    assert known_files.archive_tree_3.legacy.exists()
    assert known_files.archive_tree_4.legacy.exists()
    assert known_files.delta_cache_tree_None_1.legacy.exists()
    assert known_files.delta_cache_tree_1_2.legacy.exists()
    assert known_files.delta_cache_tree_2_3.legacy.exists()
    assert known_files.delta_cache_tree_3_4.legacy.exists()
    assert known_files.delta_cache_tree_4_ts.legacy.exists()
    assert unknown_files.inventory_tree.legacy.exists()
    assert unknown_files.inventory_tree_gz.legacy.exists()
    assert unknown_files.status_data_tree.legacy.exists()
    assert unknown_files.archive_tree_1.legacy.exists()
    assert unknown_files.archive_tree_2.legacy.exists()
    assert unknown_files.archive_tree_3.legacy.exists()
    assert unknown_files.archive_tree_4.legacy.exists()
    assert unknown_files.delta_cache_tree_None_1.legacy.exists()
    assert unknown_files.delta_cache_tree_1_2.legacy.exists()
    assert unknown_files.delta_cache_tree_2_3.legacy.exists()
    assert unknown_files.delta_cache_tree_3_4.legacy.exists()
    assert unknown_files.delta_cache_tree_4_ts.legacy.exists()
    assert not unknown_files_no_history.inventory_tree.legacy.exists()
    assert not unknown_files_no_history.inventory_tree_gz.legacy.exists()
    assert not unknown_files_no_history.status_data_tree.legacy.exists()


def test_abandoned_file_age_remaining_files_not_too_old(tmp_path: Path) -> None:
    known_files = _setup_files(tmp_path, HostName("known"), timestamp=100)
    unknown_files = _setup_files(tmp_path, HostName("unknown"), timestamp=100)
    unknown_files_no_history = _setup_files_no_history(
        tmp_path, HostName("unknown-no-history"), timestamp=100
    )
    InventoryCleanup(tmp_path)._run(
        Config(
            inventory_cleanup=InvCleanupParams(
                for_hosts=[],
                default=None,
                abandoned_file_age=2,
            )
        ),
        host_names=[HostName("known")],
        now=101,
    )
    assert known_files.inventory_tree.legacy.exists()
    assert known_files.inventory_tree_gz.legacy.exists()
    assert known_files.status_data_tree.legacy.exists()
    assert known_files.archive_tree_1.legacy.exists()
    assert known_files.archive_tree_2.legacy.exists()
    assert known_files.archive_tree_3.legacy.exists()
    assert known_files.archive_tree_4.legacy.exists()
    assert known_files.delta_cache_tree_None_1.legacy.exists()
    assert known_files.delta_cache_tree_1_2.legacy.exists()
    assert known_files.delta_cache_tree_2_3.legacy.exists()
    assert known_files.delta_cache_tree_3_4.legacy.exists()
    assert known_files.delta_cache_tree_4_ts.legacy.exists()
    assert unknown_files.inventory_tree.legacy.exists()
    assert unknown_files.inventory_tree_gz.legacy.exists()
    assert unknown_files.status_data_tree.legacy.exists()
    assert unknown_files.archive_tree_1.legacy.exists()
    assert unknown_files.archive_tree_2.legacy.exists()
    assert unknown_files.archive_tree_3.legacy.exists()
    assert unknown_files.archive_tree_4.legacy.exists()
    assert unknown_files.delta_cache_tree_None_1.legacy.exists()
    assert unknown_files.delta_cache_tree_1_2.legacy.exists()
    assert unknown_files.delta_cache_tree_2_3.legacy.exists()
    assert unknown_files.delta_cache_tree_3_4.legacy.exists()
    assert unknown_files.delta_cache_tree_4_ts.legacy.exists()
    assert unknown_files_no_history.inventory_tree.legacy.exists()
    assert unknown_files_no_history.inventory_tree_gz.legacy.exists()
    assert unknown_files_no_history.status_data_tree.legacy.exists()
