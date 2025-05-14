#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName

from cmk.utils.structured_data import InventoryPaths, TreePath, TreePathGz


@pytest.mark.parametrize(
    "raw_host_name", ["hostname", "hostname.", "hostname.domain", "hostname.json"]
)
def test_tree_paths(tmp_path: Path, raw_host_name: str) -> None:
    host_name = HostName(raw_host_name)
    inv_paths = InventoryPaths(tmp_path)
    assert inv_paths.inventory_tree(host_name) == TreePath(
        path=tmp_path / f"var/check_mk/inventory/{raw_host_name}.json",
        legacy=tmp_path / f"var/check_mk/inventory/{raw_host_name}",
    )
    assert inv_paths.inventory_tree_gz(host_name) == TreePathGz(
        path=tmp_path / f"var/check_mk/inventory/{raw_host_name}.json.gz",
        legacy=tmp_path / f"var/check_mk/inventory/{raw_host_name}.gz",
    )
    assert inv_paths.status_data_tree(host_name) == TreePath(
        path=tmp_path / f"tmp/check_mk/status_data/{raw_host_name}.json",
        legacy=tmp_path / f"tmp/check_mk/status_data/{raw_host_name}",
    )
    assert inv_paths.archive_tree(host_name, 123) == TreePath(
        path=tmp_path / f"var/check_mk/inventory_archive/{raw_host_name}/123.json",
        legacy=tmp_path / f"var/check_mk/inventory_archive/{raw_host_name}/123",
    )
    assert inv_paths.delta_cache_tree(host_name, 123, 456) == TreePath(
        path=tmp_path / f"var/check_mk/inventory_delta_cache/{raw_host_name}/123_456.json",
        legacy=tmp_path / f"var/check_mk/inventory_delta_cache/{raw_host_name}/123_456",
    )


@pytest.mark.parametrize(
    "raw_host_name", ["hostname", "hostname.", "hostname.domain", "hostname.json"]
)
@pytest.mark.parametrize(
    "directory, file_name", [("inventory_archive", "123"), ("inventory_delta_cache", "123_456")]
)
def test_tree_path_from_archive_or_delta_cache_file_path(
    tmp_path: Path, raw_host_name: str, directory: str, file_name: str
) -> None:
    assert TreePath.from_archive_or_delta_cache_file_path(
        tmp_path / f"var/check_mk/{directory}/{raw_host_name}/{file_name}.json"
    ) == TreePath(
        path=tmp_path / f"var/check_mk/{directory}/{raw_host_name}/{file_name}.json",
        legacy=tmp_path / f"var/check_mk/{directory}/{raw_host_name}/{file_name}",
    )
    assert TreePath.from_archive_or_delta_cache_file_path(
        tmp_path / f"var/check_mk/{directory}/{raw_host_name}/{file_name}"
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
