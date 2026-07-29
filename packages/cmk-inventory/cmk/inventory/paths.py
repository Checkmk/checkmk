#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostName


# TODO CMK-23408
@dataclass(frozen=True, kw_only=True)
class TreePath:
    path: Path
    legacy: Path

    def __post_init__(self) -> None:
        if self.path == Path() or self.legacy == Path():
            return
        if self.path.suffix != ".json":
            raise ValueError(self.path)

    @classmethod
    def from_archive_or_delta_cache_file_path(cls, file_path: Path) -> TreePath:
        # 'file_path' is of the form
        # - <OMD_ROOT>/var/check_mk/inventory_archive/<HOST>/<TS>.json
        # - <OMD_ROOT>/var/check_mk/inventory_archive/<HOST>/<TS>
        # - <OMD_ROOT>/var/check_mk/inventory_delta_cache/<HOST>/<TS>_<TS>.json
        # - <OMD_ROOT>/var/check_mk/inventory_delta_cache/<HOST>/<TS>_<TS>
        return (
            cls(path=file_path, legacy=file_path.with_suffix(""))
            if file_path.suffix == ".json"
            else cls(path=Path(f"{file_path}.json"), legacy=file_path)
        )


# TODO CMK-23408
@dataclass(frozen=True, kw_only=True)
class TreePathGz:
    path: Path
    legacy: Path

    def __post_init__(self) -> None:
        if self.path.suffixes[-2:] != [".json", ".gz"]:
            raise ValueError(self.path)
        if self.legacy.suffix != ".gz":
            raise ValueError(self.legacy)


class Paths:
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
        return TreePath(
            path=self.inventory_dir / f"{host_name}.json",
            legacy=self.inventory_dir / str(host_name),
        )

    def inventory_tree_gz(self, host_name: HostName) -> TreePathGz:
        return TreePathGz(
            path=self.inventory_dir / f"{host_name}.json.gz",
            legacy=self.inventory_dir / f"{host_name}.gz",
        )

    @property
    def status_data_marker_file(self) -> Path:
        return self.status_data_dir / ".last"

    def status_data_tree(self, host_name: HostName) -> TreePath:
        return TreePath(
            path=self.status_data_dir / f"{host_name}.json",
            legacy=self.status_data_dir / str(host_name),
        )

    def archive_host(self, host_name: HostName) -> Path:
        return self.archive_dir / str(host_name)

    def archive_tree(self, host_name: HostName, timestamp: int) -> TreePath:
        return TreePath(
            path=self.archive_host(host_name) / f"{timestamp}.json",
            legacy=self.archive_host(host_name) / str(timestamp),
        )

    def delta_cache_host(self, host_name: HostName) -> Path:
        return self.delta_cache_dir / str(host_name)

    def delta_cache_tree(self, host_name: HostName, previous: int, current: int) -> TreePath:
        if previous < -1 or previous >= current:
            raise ValueError(previous)
        previous_name = "None" if previous == -1 else str(previous)
        return TreePath(
            path=self.delta_cache_host(host_name) / f"{previous_name}_{current}.json",
            legacy=self.delta_cache_host(host_name) / f"{previous_name}_{current}",
        )
