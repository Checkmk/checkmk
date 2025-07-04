#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import shutil
from pathlib import Path

from cmk.ccc.hostaddress import HostName

from cmk.utils.structured_data import InventoryPaths

from cmk.gui.config import Config


class InventoryHousekeeping:
    def __init__(self, omd_root: Path) -> None:
        super().__init__()
        self.inv_paths = InventoryPaths(omd_root)

    def __call__(self, config: Config) -> None:
        if not (self.inv_paths.delta_cache_dir.exists() and self.inv_paths.archive_dir.exists()):
            return

        inventory_archive_hosts = {
            x.name for x in self.inv_paths.archive_dir.iterdir() if x.is_dir()
        }
        inventory_delta_cache_hosts = {
            x.name for x in self.inv_paths.delta_cache_dir.iterdir() if x.is_dir()
        }

        folders_to_delete = inventory_delta_cache_hosts - inventory_archive_hosts
        for foldername in folders_to_delete:
            shutil.rmtree(str(self.inv_paths.delta_cache_host(HostName(foldername))))

        inventory_delta_cache_hosts -= folders_to_delete
        for raw_host_name in inventory_delta_cache_hosts:
            host_name = HostName(raw_host_name)
            available_timestamps = self._get_timestamps_for_host(host_name)
            for file_path in [
                x for x in self.inv_paths.delta_cache_host(host_name).iterdir() if not x.is_dir()
            ]:
                delete = False
                try:
                    first, second = file_path.with_suffix("").name.split("_")
                    if not (first in available_timestamps and second in available_timestamps):
                        delete = True
                except ValueError:
                    delete = True
                if delete:
                    file_path.unlink()

    def _get_timestamps_for_host(self, host_name: HostName) -> set[str]:
        timestamps = {"None"}  # 'None' refers to the histories start
        tree_path = self.inv_paths.inventory_tree(host_name)
        try:
            timestamps.add(str(int(tree_path.stat().st_mtime)))
        except FileNotFoundError:
            # TODO CMK-23408
            try:
                timestamps.add(str(int(tree_path.legacy.stat().st_mtime)))
            except FileNotFoundError:
                pass

        for filename in [
            x for x in self.inv_paths.archive_host(host_name).iterdir() if not x.is_dir()
        ]:
            timestamps.add(filename.with_suffix("").name)
        return timestamps
