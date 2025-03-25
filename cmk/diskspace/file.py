#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import glob
import os
import random
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cmk.diskspace.free_space import fmt_bytes, get_free_space
from cmk.diskspace.logging import error, log, verbose


@dataclass(frozen=True)
class _Info:
    plugin_name: str
    path_to_mod_time: Mapping[str, float]


def _load_plugin(omd_root: Path, plugin_name: str, plugin_path: Path) -> _Info | None:
    verbose(f"Loading plugin: {plugin_path}")
    plugin: dict[str, Any] = {}
    try:
        exec(  # nosec B102 # BNS:aee528
            plugin_path.read_text(),
            plugin,
            plugin,
        )
    except Exception as e:
        error(f'Exception while loading plugin "{plugin_path}": {e}')
        return None
    # Now transform all path patterns to absolute paths for really existing files
    resolved: list[str] = []
    for path in plugin.get("cleanup_paths", []):
        # Make relative paths absolute ones
        if path[0] != "/":
            path = str(omd_root / path)

        # Resolve given path pattern to really existing files.
        # Also ensure that the files in the resolved list do really exist.
        resolved += glob.glob(path)

    path_to_mod_time = plugin.get("file_infos", {})
    for path in resolved:
        path_to_mod_time[path] = os.stat(path).st_mtime
    return _Info(plugin_name=plugin_name, path_to_mod_time=path_to_mod_time)


def load_plugins(omd_root: Path, plugin_dir: Path, plugin_dir_local: Path) -> Sequence[_Info]:
    try:
        local_plugins: list[str] = list(p.name for p in plugin_dir_local.iterdir())
    except OSError:
        local_plugins = []  # this is optional

    plugin_files: list[str] = [p.name for p in plugin_dir.iterdir() if p.name not in local_plugins]

    infos = []
    for base_dir, file_list in [(plugin_dir, plugin_files), (plugin_dir_local, local_plugins)]:
        for file_name in file_list:
            if file_name[0] == ".":
                continue
            if (info := _load_plugin(omd_root, file_name, base_dir / file_name)) is not None:
                infos.append(info)

    return infos


def _delete_file(path: str, reason: str) -> bool:
    try:
        log(f"Deleting file ({reason}): {path}")
        os.unlink(path)

        # Also delete any .info files which are connected to the RRD file
        if path.endswith(".rrd"):
            path = f"{path[:-3]}info"
            if os.path.exists(path):
                log(f"Deleting file ({reason}): {path}")
                os.unlink(path)

        return True
    except Exception as e:
        error(f"Error while deleting {path}: {e}")
    return False


def _oldest_candidate(min_file_age: int, path_to_mod_time: Mapping[str, float]) -> str | None:
    if path_to_mod_time:
        # Sort by modification time
        oldest, age = max(path_to_mod_time.items(), key=lambda key_val: key_val[1])
        if age < time.time() - min_file_age:
            return oldest
    return None


def cleanup_oldest_files(
    omd_root: Path,
    force: bool,
    min_free_bytes_and_age: tuple[int, int] | None,
    infos: Sequence[_Info],
) -> None:
    if min_free_bytes_and_age is None:
        verbose("Not cleaning up oldest files of plugins (not enabled)")
        return
    min_free_bytes, min_file_age = min_free_bytes_and_age

    # check disk space against configuration
    bytes_free: int = get_free_space(omd_root)
    if not force and bytes_free >= min_free_bytes:
        verbose(
            f"Free space is above threshold of {fmt_bytes(min_free_bytes)}. Nothing to be done."
        )
        return

    # the scheduling of the cleanup job is supposed to be equal for
    # all sites. To ensure that not only one single site is always
    # cleaning up, we add a random wait before cleanup.
    sleep_sec = float(random.randint(0, 10000)) / 1000
    verbose(f"Sleeping for {sleep_sec:0.3f} seconds")
    time.sleep(sleep_sec)

    # Loop all cleanup plugins to find the oldest candidate per plugin
    # which is older than min_age and delete this file.
    for info in infos:
        oldest = _oldest_candidate(min_file_age, info.path_to_mod_time)
        if oldest is not None and os.path.exists(oldest):  # _cleanup_aged might have deleted oldest
            _delete_file(oldest, info.plugin_name + ": my oldest")

    bytes_free = get_free_space(omd_root)
    verbose(f"Free space (after min free space space cleanup): {fmt_bytes(bytes_free)}")


def cleanup_aged(omd_root: Path, max_file_age: int | None, infos: Sequence[_Info]) -> None:
    """
    Loop all files to check whether files are older than
    max_age. Simply remove all of them.

    """
    if max_file_age is None:
        verbose("Not cleaning up too old files (not enabled)")
        return
    max_age: float = time.time() - max_file_age

    for info in infos:
        for path, mtime in info.path_to_mod_time.items():
            if mtime < max_age:
                _delete_file(path, "too old")
            else:
                verbose(f"Not deleting {path}")

    bytes_free: int = get_free_space(omd_root)
    verbose(f"Free space (after file age cleanup): {fmt_bytes(bytes_free)}")
