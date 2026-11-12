#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostName, HostNameValidationError


@dataclass(frozen=True, kw_only=True)
class TreePath:
    path: Path

    def __post_init__(self) -> None:
        if self.path.suffix != ".json":
            raise ValueError(self.path)


@dataclass(frozen=True, kw_only=True)
class TreePathGz:
    path: Path

    def __post_init__(self) -> None:
        if self.path.suffixes[-2:] != [".json", ".gz"]:
            raise ValueError(self.path)


def _file_name(host_name: HostName) -> str:
    if not host_name:
        raise HostNameValidationError("empty host name", raw=str(host_name))
    return str(HostName(host_name))


class InventoryPaths:
    def __init__(self, omd_root: Path) -> None:
        self.inventory_dir = omd_root / "var/check_mk/inventory"
        self.status_data_dir = omd_root / "tmp/check_mk/status_data"
        self.archive_dir = omd_root / "var/check_mk/inventory_archive"
        self.delta_cache_dir = omd_root / "var/check_mk/inventory_delta_cache"
        self.auto_dir = omd_root / "var/check_mk/autoinventory"

    @property
    def inventory_marker_file(self) -> Path:
        return self.inventory_dir / ".last"

    def inventory_tree(self, host_name: HostName) -> TreePath:
        return TreePath(path=self.inventory_dir / f"{_file_name(host_name)}.json")

    def inventory_tree_gz(self, host_name: HostName) -> TreePathGz:
        return TreePathGz(path=self.inventory_dir / f"{_file_name(host_name)}.json.gz")

    @property
    def status_data_marker_file(self) -> Path:
        return self.status_data_dir / ".last"

    def status_data_tree(self, host_name: HostName) -> TreePath:
        return TreePath(path=self.status_data_dir / f"{_file_name(host_name)}.json")

    def host_tree_files(self, host_name: HostName) -> Sequence[Path]:
        return [
            self.inventory_tree(host_name).path,
            self.inventory_tree_gz(host_name).path,
            self.status_data_tree(host_name).path,
        ]

    def archive_host(self, host_name: HostName) -> Path:
        return self.archive_dir / _file_name(host_name)

    def archive_tree(self, host_name: HostName, timestamp: int) -> TreePath:
        return TreePath(path=self.archive_host(host_name) / f"{timestamp}.json")

    def delta_cache_host(self, host_name: HostName) -> Path:
        return self.delta_cache_dir / _file_name(host_name)

    def delta_cache_tree(self, host_name: HostName, previous: int, current: int) -> TreePath:
        if previous < -1 or previous >= current:
            raise ValueError(previous)
        previous_name = "None" if previous == -1 else str(previous)
        return TreePath(path=self.delta_cache_host(host_name) / f"{previous_name}_{current}.json")


def collect_files(directory: Path) -> Sequence[Path]:
    try:
        return list(directory.iterdir())
    except FileNotFoundError:
        return []


def tree_mtime(tree_path: TreePath) -> int | None:
    try:
        return int(tree_path.path.stat().st_mtime)
    except FileNotFoundError:
        return None


def has_inventory_tree(inv_paths: InventoryPaths, host_name: HostName) -> bool:
    return inv_paths.inventory_tree(host_name).path.exists()


def has_status_data_tree(inv_paths: InventoryPaths, host_name: HostName) -> bool:
    return inv_paths.status_data_tree(host_name).path.exists()


def _has_files(directory: Path) -> bool:
    try:
        return any(directory.iterdir())
    except FileNotFoundError:
        return False


def has_archive(inv_paths: InventoryPaths, host_name: HostName) -> bool:
    return _has_files(inv_paths.archive_host(host_name))


def has_history(inv_paths: InventoryPaths, host_name: HostName) -> bool:
    return has_archive(inv_paths, host_name) or _has_files(inv_paths.delta_cache_host(host_name))


def parse_archive_timestamp(file_path: Path) -> int:
    return int(file_path.with_suffix("").name)


def parse_delta_cache_timestamps(file_path: Path) -> tuple[int, int]:
    previous_name, current_name = file_path.with_suffix("").name.split("_")
    return -1 if previous_name == "None" else int(previous_name), int(current_name)
