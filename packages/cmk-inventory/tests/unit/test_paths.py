#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName, HostNameValidationError
from cmk.inventory.paths import (
    InventoryPaths,
    parse_archive_timestamp,
    parse_delta_cache_timestamps,
    TreePath,
    TreePathGz,
)

_OMD_ROOT = Path("/omd_root")


@pytest.mark.parametrize(
    "raw_host_name", ["hostname", "hostname.", "hostname.domain", "hostname.json"]
)
def test_tree_paths(raw_host_name: str) -> None:
    host_name = HostName(raw_host_name)
    inv_paths = InventoryPaths(_OMD_ROOT)
    assert (
        inv_paths.inventory_tree(host_name),
        inv_paths.inventory_tree_gz(host_name),
        inv_paths.status_data_tree(host_name),
        inv_paths.archive_tree(host_name, 123),
        inv_paths.delta_cache_tree(host_name, 123, 456),
    ) == (
        TreePath(
            path=_OMD_ROOT / f"var/check_mk/inventory/{raw_host_name}.json",
        ),
        TreePathGz(
            path=_OMD_ROOT / f"var/check_mk/inventory/{raw_host_name}.json.gz",
        ),
        TreePath(
            path=_OMD_ROOT / f"tmp/check_mk/status_data/{raw_host_name}.json",
        ),
        TreePath(
            path=_OMD_ROOT / f"var/check_mk/inventory_archive/{raw_host_name}/123.json",
        ),
        TreePath(
            path=_OMD_ROOT / f"var/check_mk/inventory_delta_cache/{raw_host_name}/123_456.json",
        ),
    )


@pytest.mark.parametrize(
    "previous, current, expected_name",
    [
        pytest.param(-1, 0, "None_0", id="history-start"),
        pytest.param(123, 456, "123_456", id="pair"),
    ],
)
def test_delta_cache_tree(previous: int, current: int, expected_name: str) -> None:
    assert InventoryPaths(_OMD_ROOT).delta_cache_tree(
        HostName("hostname"), previous, current
    ) == TreePath(
        path=_OMD_ROOT / f"var/check_mk/inventory_delta_cache/hostname/{expected_name}.json"
    )


@pytest.mark.parametrize(
    "previous, current",
    [
        pytest.param(-2, 0, id="previous-too-low"),
        pytest.param(1, 0, id="previous-greater-current"),
        pytest.param(-1, -1, id="previous-equal-current"),
    ],
)
def test_delta_cache_tree_error(previous: int, current: int) -> None:
    with pytest.raises(ValueError):
        InventoryPaths(_OMD_ROOT).delta_cache_tree(HostName("hostname"), previous, current)


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
        TreePath(path=Path("hostname.gz"))


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(Path("hostname.json"), id="not-gzipped"),
        pytest.param(Path("hostname.gz"), id="without-json"),
    ],
)
def test_tree_path_gz_rejects_a_misnamed_path(path: Path) -> None:
    with pytest.raises(ValueError):
        TreePathGz(path=path)


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
    path_of: Callable[[InventoryPaths, HostName], object], host_name: HostName
) -> None:
    with pytest.raises(HostNameValidationError):
        path_of(InventoryPaths(_OMD_ROOT), host_name)


def test_host_tree_files() -> None:
    assert [
        str(p.relative_to(_OMD_ROOT))
        for p in InventoryPaths(_OMD_ROOT).host_tree_files(HostName("host"))
    ] == [
        "var/check_mk/inventory/host.json",
        "var/check_mk/inventory/host.json.gz",
        "tmp/check_mk/status_data/host.json",
    ]
