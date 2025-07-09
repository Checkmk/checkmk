#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from dataclasses import dataclass
from pathlib import Path

from cmk.utils.hostaddress import HostName

from cmk.gui.config import Config
from cmk.gui.inventory._cleanup import (
    InventoryCleanup,
)

from cmk.inventory.config import (
    InvCleanupParams,
    InvCleanupParamsCombined,
    InvCleanupParamsOfHosts,
)


def test_nothing_to_do(tmp_path: Path) -> None:
    archive_host = tmp_path / "var/check_mk/inventory_archive/hostname"
    delta_cache_host = tmp_path / "var/check_mk/inventory_delta_cache/hostname"

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
    archive_host = tmp_path / "var/check_mk/inventory_archive/hostname"
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = tmp_path / "var/check_mk/inventory_delta_cache/hostname"

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
    archive_host = tmp_path / "var/check_mk/inventory_archive/hostname"
    delta_cache_host = tmp_path / "var/check_mk/inventory_delta_cache/hostname"
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
    archive_host = tmp_path / "var/check_mk/inventory_archive/hostname"
    archive_host.mkdir(parents=True, exist_ok=True)
    delta_cache_host = tmp_path / "var/check_mk/inventory_delta_cache/hostname"
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
    inventory_tree: Path
    inventory_tree_gz: Path
    status_data_tree: Path
    archive_tree: Path


def _setup_one_archive_file(tmp_path: Path, *, timestamp: int) -> _OneArchiveFile:
    host_name = HostName("hostname")

    inventory_tree = tmp_path / f"var/check_mk/inventory/{host_name}"
    inventory_tree.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.touch()
    os.utime(inventory_tree, (timestamp, timestamp))

    inventory_tree_gz = tmp_path / f"var/check_mk/inventory/{host_name}.gz"
    inventory_tree_gz.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.touch()
    os.utime(inventory_tree_gz, (timestamp, timestamp))

    status_data_tree = tmp_path / f"tmp/check_mk/status_data/{host_name}"
    status_data_tree.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.touch()
    os.utime(status_data_tree, (timestamp, timestamp))

    archive_tree = tmp_path / f"var/check_mk/inventory_archive/{host_name}/{timestamp-1}"
    archive_tree.parent.mkdir(parents=True, exist_ok=True)
    archive_tree.touch()

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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert files.archive_tree.exists()


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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree.exists()


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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert files.archive_tree.exists()


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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree.exists()


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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree.exists()


@dataclass(frozen=True, kw_only=True)
class _Files:
    inventory_tree: Path
    inventory_tree_gz: Path
    status_data_tree: Path
    archive_tree_1: Path
    archive_tree_2: Path
    archive_tree_3: Path
    archive_tree_4: Path
    delta_cache_tree_None_1: Path
    delta_cache_tree_1_2: Path
    delta_cache_tree_2_3: Path
    delta_cache_tree_3_4: Path
    delta_cache_tree_4_ts: Path


def _setup_files(tmp_path: Path, host_name: HostName, *, timestamp: int) -> _Files:
    inventory_tree = tmp_path / f"var/check_mk/inventory/{host_name}"
    inventory_tree.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.touch()
    os.utime(inventory_tree, (timestamp, timestamp))

    inventory_tree_gz = tmp_path / f"var/check_mk/inventory/{host_name}.gz"
    inventory_tree_gz.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.touch()
    os.utime(inventory_tree_gz, (timestamp, timestamp))

    status_data_tree = tmp_path / f"tmp/check_mk/status_data/{host_name}"
    status_data_tree.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.touch()
    os.utime(status_data_tree, (timestamp, timestamp))

    archive_tree_1 = tmp_path / f"var/check_mk/inventory_archive/{host_name}/{timestamp-4}"
    archive_tree_2 = tmp_path / f"var/check_mk/inventory_archive/{host_name}/{timestamp-3}"
    archive_tree_3 = tmp_path / f"var/check_mk/inventory_archive/{host_name}/{timestamp-2}"
    archive_tree_4 = tmp_path / f"var/check_mk/inventory_archive/{host_name}/{timestamp-1}"
    delta_cache_tree_None_1 = (
        tmp_path / f"var/check_mk/inventory_delta_cache/{host_name}/None_{timestamp-4}"
    )
    delta_cache_tree_1_2 = (
        tmp_path / f"var/check_mk/inventory_delta_cache/{host_name}/{timestamp-4}_{timestamp-3}"
    )
    delta_cache_tree_2_3 = (
        tmp_path / f"var/check_mk/inventory_delta_cache/{host_name}/{timestamp-3}_{timestamp-2}"
    )
    delta_cache_tree_3_4 = (
        tmp_path / f"var/check_mk/inventory_delta_cache/{host_name}/{timestamp-2}_{timestamp-1}"
    )
    delta_cache_tree_4_ts = (
        tmp_path / f"var/check_mk/inventory_delta_cache/{host_name}/{timestamp-1}_{timestamp}"
    )

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
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree_1.exists()
    assert not files.archive_tree_2.exists()
    assert files.archive_tree_3.exists()
    assert files.archive_tree_4.exists()
    assert not files.delta_cache_tree_None_1.exists()
    assert not files.delta_cache_tree_1_2.exists()
    assert not files.delta_cache_tree_2_3.exists()
    assert files.delta_cache_tree_3_4.exists()
    assert not files.delta_cache_tree_4_ts.exists()


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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree_1.exists()
    assert files.archive_tree_2.exists()
    assert files.archive_tree_3.exists()
    assert files.archive_tree_4.exists()
    assert not files.delta_cache_tree_None_1.exists()
    assert not files.delta_cache_tree_1_2.exists()
    assert files.delta_cache_tree_2_3.exists()
    assert files.delta_cache_tree_3_4.exists()
    assert not files.delta_cache_tree_4_ts.exists()


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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree_1.exists()
    assert files.archive_tree_2.exists()
    assert files.archive_tree_3.exists()
    assert files.archive_tree_4.exists()
    assert not files.delta_cache_tree_None_1.exists()
    assert not files.delta_cache_tree_1_2.exists()
    assert files.delta_cache_tree_2_3.exists()
    assert files.delta_cache_tree_3_4.exists()
    assert not files.delta_cache_tree_4_ts.exists()


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
    assert files.inventory_tree.exists()
    assert files.inventory_tree_gz.exists()
    assert files.status_data_tree.exists()
    assert not files.archive_tree_1.exists()
    assert not files.archive_tree_2.exists()
    assert files.archive_tree_3.exists()
    assert files.archive_tree_4.exists()
    assert not files.delta_cache_tree_None_1.exists()
    assert not files.delta_cache_tree_1_2.exists()
    assert not files.delta_cache_tree_2_3.exists()
    assert files.delta_cache_tree_3_4.exists()
    assert not files.delta_cache_tree_4_ts.exists()


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
    assert known_files.inventory_tree.exists()
    assert known_files.inventory_tree_gz.exists()
    assert known_files.status_data_tree.exists()
    assert known_files.archive_tree_1.exists()
    assert known_files.archive_tree_2.exists()
    assert known_files.archive_tree_3.exists()
    assert known_files.archive_tree_4.exists()
    assert known_files.delta_cache_tree_None_1.exists()
    assert known_files.delta_cache_tree_1_2.exists()
    assert known_files.delta_cache_tree_2_3.exists()
    assert known_files.delta_cache_tree_3_4.exists()
    assert known_files.delta_cache_tree_4_ts.exists()
    assert not unknown_files.inventory_tree.exists()
    assert not unknown_files.inventory_tree_gz.exists()
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
    assert not unknown_files.delta_cache_tree_4_ts.exists()
    assert not unknown_files.delta_cache_tree_4_ts.parent.exists()


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
    assert known_files.inventory_tree.exists()
    assert known_files.inventory_tree_gz.exists()
    assert known_files.status_data_tree.exists()
    assert known_files.archive_tree_1.exists()
    assert known_files.archive_tree_2.exists()
    assert known_files.archive_tree_3.exists()
    assert known_files.archive_tree_4.exists()
    assert known_files.delta_cache_tree_None_1.exists()
    assert known_files.delta_cache_tree_1_2.exists()
    assert known_files.delta_cache_tree_2_3.exists()
    assert known_files.delta_cache_tree_3_4.exists()
    assert known_files.delta_cache_tree_4_ts.exists()
    assert unknown_files.inventory_tree.exists()
    assert unknown_files.inventory_tree_gz.exists()
    assert unknown_files.status_data_tree.exists()
    assert unknown_files.archive_tree_1.exists()
    assert unknown_files.archive_tree_2.exists()
    assert unknown_files.archive_tree_3.exists()
    assert unknown_files.archive_tree_4.exists()
    assert unknown_files.delta_cache_tree_None_1.exists()
    assert unknown_files.delta_cache_tree_1_2.exists()
    assert unknown_files.delta_cache_tree_2_3.exists()
    assert unknown_files.delta_cache_tree_3_4.exists()
    assert unknown_files.delta_cache_tree_4_ts.exists()


@dataclass(frozen=True, kw_only=True)
class _FilesNoHistory:
    inventory_tree: Path
    inventory_tree_gz: Path
    status_data_tree: Path


def _setup_files_no_history(
    tmp_path: Path, host_name: HostName, *, timestamp: int
) -> _FilesNoHistory:
    inventory_tree = tmp_path / f"var/check_mk/inventory/{host_name}"
    inventory_tree.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree.touch()
    os.utime(inventory_tree, (timestamp, timestamp))

    inventory_tree_gz = tmp_path / f"var/check_mk/inventory/{host_name}.gz"
    inventory_tree_gz.parent.mkdir(parents=True, exist_ok=True)
    inventory_tree_gz.touch()
    os.utime(inventory_tree_gz, (timestamp, timestamp))

    status_data_tree = tmp_path / f"tmp/check_mk/status_data/{host_name}"
    status_data_tree.parent.mkdir(parents=True, exist_ok=True)
    status_data_tree.touch()
    os.utime(status_data_tree, (timestamp, timestamp))

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
    assert known_files.inventory_tree.exists()
    assert known_files.inventory_tree_gz.exists()
    assert known_files.status_data_tree.exists()
    assert known_files.archive_tree_1.exists()
    assert known_files.archive_tree_2.exists()
    assert known_files.archive_tree_3.exists()
    assert known_files.archive_tree_4.exists()
    assert known_files.delta_cache_tree_None_1.exists()
    assert known_files.delta_cache_tree_1_2.exists()
    assert known_files.delta_cache_tree_2_3.exists()
    assert known_files.delta_cache_tree_3_4.exists()
    assert known_files.delta_cache_tree_4_ts.exists()
    assert unknown_files.inventory_tree.exists()
    assert unknown_files.inventory_tree_gz.exists()
    assert unknown_files.status_data_tree.exists()
    assert unknown_files.archive_tree_1.exists()
    assert unknown_files.archive_tree_2.exists()
    assert unknown_files.archive_tree_3.exists()
    assert unknown_files.archive_tree_4.exists()
    assert unknown_files.delta_cache_tree_None_1.exists()
    assert unknown_files.delta_cache_tree_1_2.exists()
    assert unknown_files.delta_cache_tree_2_3.exists()
    assert unknown_files.delta_cache_tree_3_4.exists()
    assert unknown_files.delta_cache_tree_4_ts.exists()
    assert not unknown_files_no_history.inventory_tree.exists()
    assert not unknown_files_no_history.inventory_tree_gz.exists()
    assert not unknown_files_no_history.status_data_tree.exists()


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
    assert known_files.inventory_tree.exists()
    assert known_files.inventory_tree_gz.exists()
    assert known_files.status_data_tree.exists()
    assert known_files.archive_tree_1.exists()
    assert known_files.archive_tree_2.exists()
    assert known_files.archive_tree_3.exists()
    assert known_files.archive_tree_4.exists()
    assert known_files.delta_cache_tree_None_1.exists()
    assert known_files.delta_cache_tree_1_2.exists()
    assert known_files.delta_cache_tree_2_3.exists()
    assert known_files.delta_cache_tree_3_4.exists()
    assert known_files.delta_cache_tree_4_ts.exists()
    assert unknown_files.inventory_tree.exists()
    assert unknown_files.inventory_tree_gz.exists()
    assert unknown_files.status_data_tree.exists()
    assert unknown_files.archive_tree_1.exists()
    assert unknown_files.archive_tree_2.exists()
    assert unknown_files.archive_tree_3.exists()
    assert unknown_files.archive_tree_4.exists()
    assert unknown_files.delta_cache_tree_None_1.exists()
    assert unknown_files.delta_cache_tree_1_2.exists()
    assert unknown_files.delta_cache_tree_2_3.exists()
    assert unknown_files.delta_cache_tree_3_4.exists()
    assert unknown_files.delta_cache_tree_4_ts.exists()
    assert unknown_files_no_history.inventory_tree.exists()
    assert unknown_files_no_history.inventory_tree_gz.exists()
    assert unknown_files_no_history.status_data_tree.exists()
