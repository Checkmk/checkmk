#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName, HostNameValidationError
from cmk.inventory.paths import (
    has_archive,
    has_history,
    has_inventory_tree,
    has_status_data_tree,
    InventoryPaths,
    parse_archive_timestamp,
    parse_delta_cache_timestamps,
    tree_mtime,
    TreePath,
    TreePathGz,
)


@pytest.mark.parametrize(
    "raw_host_name", ["hostname", "hostname.", "hostname.domain", "hostname.json"]
)
def test_tree_paths(tmp_path: Path, raw_host_name: str) -> None:
    host_name = HostName(raw_host_name)
    inv_paths = InventoryPaths(tmp_path)
    assert (
        inv_paths.inventory_tree(host_name),
        inv_paths.inventory_tree_gz(host_name),
        inv_paths.status_data_tree(host_name),
        inv_paths.archive_tree(host_name, 123),
        inv_paths.delta_cache_tree(host_name, 123, 456),
    ) == (
        TreePath(
            path=tmp_path / f"var/check_mk/inventory/{raw_host_name}.json",
            legacy=tmp_path / f"var/check_mk/inventory/{raw_host_name}",
        ),
        TreePathGz(
            path=tmp_path / f"var/check_mk/inventory/{raw_host_name}.json.gz",
            legacy=tmp_path / f"var/check_mk/inventory/{raw_host_name}.gz",
        ),
        TreePath(
            path=tmp_path / f"tmp/check_mk/status_data/{raw_host_name}.json",
            legacy=tmp_path / f"tmp/check_mk/status_data/{raw_host_name}",
        ),
        TreePath(
            path=tmp_path / f"var/check_mk/inventory_archive/{raw_host_name}/123.json",
            legacy=tmp_path / f"var/check_mk/inventory_archive/{raw_host_name}/123",
        ),
        TreePath(
            path=tmp_path / f"var/check_mk/inventory_delta_cache/{raw_host_name}/123_456.json",
            legacy=tmp_path / f"var/check_mk/inventory_delta_cache/{raw_host_name}/123_456",
        ),
    )


@pytest.mark.parametrize(
    "raw_host_name", ["hostname", "hostname.", "hostname.domain", "hostname.json"]
)
@pytest.mark.parametrize(
    "directory, file_name", [("inventory_archive", "123"), ("inventory_delta_cache", "123_456")]
)
@pytest.mark.parametrize("suffix", ["", ".json"])
def test_tree_path_from_archive_or_delta_cache_file_path(
    tmp_path: Path, raw_host_name: str, directory: str, file_name: str, suffix: str
) -> None:
    assert TreePath.from_archive_or_delta_cache_file_path(
        tmp_path / f"var/check_mk/{directory}/{raw_host_name}/{file_name}{suffix}"
    ) == TreePath(
        path=tmp_path / f"var/check_mk/{directory}/{raw_host_name}/{file_name}.json",
        legacy=tmp_path / f"var/check_mk/{directory}/{raw_host_name}/{file_name}",
    )


@pytest.mark.parametrize(
    "previous, current, expected_name",
    [
        pytest.param(-1, 0, "None_0", id="history-start"),
        pytest.param(123, 456, "123_456", id="pair"),
    ],
)
def test_delta_cache_tree(tmp_path: Path, previous: int, current: int, expected_name: str) -> None:
    file_path = tmp_path / f"var/check_mk/inventory_delta_cache/hostname/{expected_name}"
    assert InventoryPaths(tmp_path).delta_cache_tree(
        HostName("hostname"), previous, current
    ) == TreePath(path=file_path.with_suffix(".json"), legacy=file_path)


@pytest.mark.parametrize(
    "previous, current",
    [
        pytest.param(-2, 0, id="previous-too-low"),
        pytest.param(1, 0, id="previous-greater-current"),
        pytest.param(-1, -1, id="previous-equal-current"),
    ],
)
def test_delta_cache_tree_error(tmp_path: Path, previous: int, current: int) -> None:
    with pytest.raises(ValueError):
        InventoryPaths(tmp_path).delta_cache_tree(HostName("hostname"), previous, current)


def test_parse_archive_timestamp() -> None:
    assert parse_archive_timestamp(Path("/var/check_mk/inventory_archive/hostname/123.json")) == 123


def test_parse_archive_timestamp_of_a_legacy_file() -> None:
    assert parse_archive_timestamp(Path("/var/check_mk/inventory_archive/hostname/123")) == 123


def test_parse_archive_timestamp_of_an_unknown_file() -> None:
    with pytest.raises(ValueError):
        parse_archive_timestamp(Path("/var/check_mk/inventory_archive/hostname/not-a-timestamp"))


def test_parse_delta_cache_timestamps() -> None:
    assert parse_delta_cache_timestamps(
        Path("/var/check_mk/inventory_delta_cache/hostname/1_2.json")
    ) == (1, 2)


def test_parse_delta_cache_timestamps_without_a_previous_tree() -> None:
    assert parse_delta_cache_timestamps(
        Path("/var/check_mk/inventory_delta_cache/hostname/None_2.json")
    ) == (-1, 2)


def test_parse_delta_cache_timestamps_of_an_unknown_file() -> None:
    with pytest.raises(ValueError):
        parse_delta_cache_timestamps(Path("/var/check_mk/inventory_delta_cache/hostname/2.json"))


def test_tree_path_rejects_a_path_without_json_suffix() -> None:
    with pytest.raises(ValueError):
        TreePath(path=Path("hostname.gz"), legacy=Path("hostname"))


@pytest.mark.parametrize(
    "path, legacy",
    [
        pytest.param(Path("hostname.json"), Path("hostname.gz"), id="path-not-gzipped"),
        pytest.param(Path("hostname.gz"), Path("hostname.gz"), id="path-without-json"),
        pytest.param(Path("hostname.json.gz"), Path("hostname"), id="legacy-not-gzipped"),
    ],
)
def test_tree_path_gz_rejects_a_misnamed_path(path: Path, legacy: Path) -> None:
    with pytest.raises(ValueError):
        TreePathGz(path=path, legacy=legacy)


@pytest.mark.parametrize(
    "path_of",
    [
        InventoryPaths.inventory_tree,
        InventoryPaths.inventory_tree_gz,
        InventoryPaths.status_data_tree,
        InventoryPaths.archive_host,
        InventoryPaths.delta_cache_host,
    ],
)
@pytest.mark.parametrize(
    "host_name", [json.loads('".."'), HostName("")], ids=["parent directory", "empty"]
)
def test_tree_paths_refuse_a_host_name_leaving_their_directory(
    tmp_path: Path, path_of: Callable[[InventoryPaths, HostName], object], host_name: HostName
) -> None:
    with pytest.raises(HostNameValidationError):
        path_of(InventoryPaths(tmp_path), host_name)


def test_has_inventory_tree(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inv_paths.inventory_dir.mkdir(parents=True)
    inv_paths.inventory_tree(HostName("host")).path.touch()
    assert has_inventory_tree(inv_paths, HostName("host"))


def test_has_inventory_tree_of_a_legacy_file(tmp_path: Path) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inv_paths.inventory_dir.mkdir(parents=True)
    inv_paths.inventory_tree(HostName("host")).legacy.touch()
    assert has_inventory_tree(inv_paths, HostName("host"))


def test_has_no_inventory_tree(tmp_path: Path) -> None:
    assert not has_inventory_tree(InventoryPaths(tmp_path), HostName("host"))


@pytest.mark.parametrize("legacy", [False, True])
def test_has_status_data_tree(tmp_path: Path, legacy: bool) -> None:
    inv_paths = InventoryPaths(tmp_path)
    inv_paths.status_data_dir.mkdir(parents=True)
    tree_path = inv_paths.status_data_tree(HostName("host"))
    (tree_path.legacy if legacy else tree_path.path).touch()
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


def test_host_tree_files(tmp_path: Path) -> None:
    assert [
        str(p.relative_to(tmp_path))
        for p in InventoryPaths(tmp_path).host_tree_files(HostName("host"))
    ] == [
        "var/check_mk/inventory/host.json",
        "var/check_mk/inventory/host",
        "var/check_mk/inventory/host.json.gz",
        "var/check_mk/inventory/host.gz",
        "tmp/check_mk/status_data/host.json",
        "tmp/check_mk/status_data/host",
    ]


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
