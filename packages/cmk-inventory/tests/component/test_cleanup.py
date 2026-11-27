#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.cleanup import InventoryCleanup
from cmk.inventory.config import (
    InvCleanupParams,
    InvCleanupParamsChoice,
    InvCleanupParamsCombined,
    InvCleanupParamsOfHosts,
)
from cmk.inventory.paths import InventoryPaths

from ._logger import null_logger

_NOW = 101
_TIMESTAMP = 100


def _for_hostname(parameters: InvCleanupParamsChoice) -> InvCleanupParams:
    return InvCleanupParams(
        for_hosts=[InvCleanupParamsOfHosts(regex_or_explicit=["hostname"], parameters=parameters)],
        default=None,
        abandoned_file_age=1,
    )


def _abandoned_only(abandoned_file_age: int) -> InvCleanupParams:
    return InvCleanupParams(for_hosts=[], default=None, abandoned_file_age=abandoned_file_age)


def _combined(
    strategy: Literal["and", "or"], file_age: int, number_of_history_entries: int
) -> InvCleanupParams:
    return _for_hostname(
        (
            "combined",
            InvCleanupParamsCombined(
                strategy=strategy,
                file_age=file_age,
                number_of_history_entries=number_of_history_entries,
            ),
        )
    )


def _run(omd_root: Path, params: InvCleanupParams, *, host_names: Sequence[HostName]) -> None:
    InventoryCleanup(omd_root).run(params, host_names=host_names, now=_NOW, logger=null_logger())


def _create(file_path: Path) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch()
    return file_path


def _create_tree_files(omd_root: Path, host_name: HostName, *, mtime: int) -> Mapping[str, Path]:
    inv_paths = InventoryPaths(omd_root)
    files = {
        "inventory": _create(inv_paths.inventory_tree(host_name).path),
        "inventory gz": _create(inv_paths.inventory_tree_gz(host_name).path),
        "status data": _create(inv_paths.status_data_tree(host_name).path),
    }
    for file_path in files.values():
        os.utime(file_path, (mtime, mtime))
    return files


def _create_one_archive_file(omd_root: Path) -> Mapping[str, Path]:
    archive_tree = InventoryPaths(omd_root).archive_tree(HostName("hostname"), _TIMESTAMP - 1)
    return {
        **_create_tree_files(omd_root, HostName("hostname"), mtime=_TIMESTAMP),
        "archive 99": _create(archive_tree.path),
    }


def _create_history_files(omd_root: Path, host_name: HostName) -> Mapping[str, Path]:
    inv_paths = InventoryPaths(omd_root)
    archive_files = {
        f"archive {ts}": _create(inv_paths.archive_tree(host_name, ts).path)
        for ts in range(96, 100)
    }
    delta_cache_files = {
        f"delta {ts}_{ts + 1}": _create(inv_paths.delta_cache_tree(host_name, ts, ts + 1).path)
        for ts in range(95, 100)
    }
    return {
        **_create_tree_files(omd_root, host_name, mtime=_TIMESTAMP),
        **archive_files,
        **delta_cache_files,
        "archive dir": inv_paths.archive_host(host_name),
        "delta cache dir": inv_paths.delta_cache_host(host_name),
    }


def _removed(files: Mapping[str, Path]) -> Sequence[str]:
    return [label for label, file_path in files.items() if not file_path.exists()]


@pytest.mark.parametrize(
    "created",
    [
        pytest.param([], id="none"),
        pytest.param(["archive"], id="archive"),
        pytest.param(["delta cache"], id="delta-cache"),
        pytest.param(["archive", "delta cache"], id="both"),
    ],
)
def test_cleanup_leaves_the_history_directories_as_they_are(
    tmp_path: Path, created: Sequence[str]
) -> None:
    inv_paths = InventoryPaths(tmp_path)
    directories = {
        "archive": inv_paths.archive_host(HostName("hostname")),
        "delta cache": inv_paths.delta_cache_host(HostName("hostname")),
    }
    for name in created:
        directories[name].mkdir(parents=True)

    _run(tmp_path, _abandoned_only(100), host_names=[HostName("hostname")])

    assert [name for name, directory in directories.items() if directory.exists()] == created


@pytest.mark.parametrize(
    "params, removed",
    [
        pytest.param(_abandoned_only(1), [], id="no-parameters"),
        pytest.param(_for_hostname(("file_age", 2)), ["archive 99"], id="file-age"),
        pytest.param(
            _for_hostname(("number_of_history_entries", 1)), [], id="number-of-history-entries"
        ),
        pytest.param(_combined("and", 2, 1), ["archive 99"], id="and"),
        pytest.param(_combined("or", 2, 1), ["archive 99"], id="or"),
    ],
)
def test_cleanup_of_a_single_archive_file(
    tmp_path: Path, params: InvCleanupParams, removed: Sequence[str]
) -> None:
    files = _create_one_archive_file(tmp_path)

    _run(tmp_path, params, host_names=[HostName("hostname")])

    assert _removed(files) == removed


_TOO_OLD = ["archive 96", "archive 97", "delta 95_96", "delta 96_97", "delta 97_98"]
_BEYOND_NUMBER = ["archive 96", "delta 95_96", "delta 96_97"]


@pytest.mark.parametrize(
    "params, removed",
    [
        pytest.param(_for_hostname(("file_age", 3)), _TOO_OLD, id="file-age"),
        pytest.param(
            _for_hostname(("number_of_history_entries", 2)),
            _BEYOND_NUMBER,
            id="number-of-history-entries",
        ),
        pytest.param(_combined("and", 3, 2), _BEYOND_NUMBER, id="and"),
        pytest.param(_combined("or", 3, 2), _TOO_OLD, id="or"),
    ],
)
def test_cleanup_of_a_history(
    tmp_path: Path, params: InvCleanupParams, removed: Sequence[str]
) -> None:
    files = _create_history_files(tmp_path, HostName("hostname"))

    _run(tmp_path, params, host_names=[HostName("hostname")])

    assert _removed(files) == [*removed, "delta 99_100"]


def test_cleanup_removes_an_abandoned_host_whose_youngest_file_is_too_old(tmp_path: Path) -> None:
    known = _create_history_files(tmp_path, HostName("known"))
    unknown = _create_history_files(tmp_path, HostName("unknown"))

    _run(tmp_path, _abandoned_only(1), host_names=[HostName("known")])

    assert (_removed(known), _removed(unknown)) == ([], list(unknown))


def test_cleanup_keeps_an_abandoned_host_whose_youngest_file_is_not_too_old(tmp_path: Path) -> None:
    known = _create_history_files(tmp_path, HostName("known"))
    unknown = _create_history_files(tmp_path, HostName("unknown"))

    _run(tmp_path, _abandoned_only(2), host_names=[HostName("known")])

    assert (_removed(known), _removed(unknown)) == ([], [])


@pytest.mark.parametrize(
    "mtime, removed",
    [
        pytest.param(99, ["inventory", "inventory gz", "status data"], id="too-old"),
        pytest.param(100, [], id="not-too-old"),
    ],
)
def test_cleanup_of_the_tree_files_of_an_abandoned_host_without_history(
    tmp_path: Path, mtime: int, removed: Sequence[str]
) -> None:
    _create_history_files(tmp_path, HostName("known"))
    _create_history_files(tmp_path, HostName("unknown"))
    files = _create_tree_files(tmp_path, HostName("unknown-no-history"), mtime=mtime)

    _run(tmp_path, _abandoned_only(2), host_names=[HostName("known")])

    assert _removed(files) == removed


def test_file_age_removes_an_archive_file_dated_at_the_epoch(tmp_path: Path) -> None:
    archive_file = _create(InventoryPaths(tmp_path).archive_tree(HostName("hostname"), 0).path)

    _run(tmp_path, _for_hostname(("file_age", 3)), host_names=[HostName("hostname")])

    assert not archive_file.exists()


def test_without_host_names_no_abandoned_file_is_removed(tmp_path: Path) -> None:
    abandoned_file = _create(tmp_path / "var/check_mk/inventory/unknown-host.json")
    os.utime(abandoned_file, (0, 0))

    _run(tmp_path, _abandoned_only(1), host_names=[])

    assert abandoned_file.exists()


@pytest.mark.parametrize(
    "file_name",
    [
        pytest.param("inventory_archive/hostname/not-a-timestamp", id="archive"),
        pytest.param("inventory_delta_cache/hostname/not-a-timestamp", id="delta-cache"),
    ],
)
def test_a_history_file_without_timestamps_is_kept(tmp_path: Path, file_name: str) -> None:
    file_path = _create(tmp_path / "var/check_mk" / file_name)

    _run(tmp_path, _for_hostname(("file_age", 1)), host_names=[HostName("hostname")])

    assert file_path.exists()
