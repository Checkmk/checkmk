#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow-any-generics
# mypy: disallow-any-decorated
# mypy: disallow-any-unimported
# mypy: disallow-subclassing-any

import glob
import logging
import os
import random
import subprocess
import sys
import time
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from omdlib.utils import get_site_distributed_setup, SiteDistributedSetup

from cmk.utils.paths import diskspace_config_dir, omd_root, var_dir
from cmk.utils.render import fmt_bytes

# TODO: The diskspace tool depends on `check_mk` as a cli tool. Therefore, having the
# "site context" as a dependency is probably appropriate. It could be moved to `cmk/diskspace`,
# but that is also suboptimal, since the tool depends on `omdlib`.
from cmk.diskspace import Config, read_config  # pylint: disable=cmk-module-layer-violation


def _error(message: str) -> None:
    sys.stderr.write(f"ERROR: {message}\n")


def _log(message: str) -> None:
    logging.getLogger(__name__).info(message)


def _verbose(message: str) -> None:
    logging.getLogger(__name__).debug(message)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=logging.DEBUG if verbose else logging.INFO
    )


def _print_config(config: Config) -> None:
    _verbose("Settings:")
    if config.cleanup_abandoned_host_files is None:
        _verbose("  Not cleaning up abandoned host files.")
    else:
        _verbose(
            "  Cleaning up abandoned host files older than %d seconds."
            % int(config.cleanup_abandoned_host_files)
        )

    if config.max_file_age is None:
        _verbose("  Not cleaning up files by age.")
    else:
        _verbose("  Cleanup files that are older than %d seconds." % config.max_file_age)

    match config.min_free_bytes:
        case None:
            _verbose("  Not cleaning up files by free space left.")
        case (bytes_, age):
            _verbose(
                "  Cleanup files till %s are free while not deleting files "
                "older than %d seconds" % (fmt_bytes(bytes_), age)
            )


@dataclass(frozen=True)
class _Info:
    plugin_name: str
    path_to_mod_time: Mapping[str, float]


def _load_plugin(plugin_name: str, plugin_path: Path) -> _Info | None:
    _verbose(f"Loading plugin: {plugin_path}")
    plugin: dict[str, Any] = {}
    try:
        exec(  # nosec B102 # BNS:aee528
            plugin_path.read_text(),
            plugin,
            plugin,
        )
    except Exception as e:
        _error(f'Exception while loading plugin "{plugin_path}": {e}')
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


def _load_plugins(plugin_dir: Path, plugin_dir_local: Path) -> Sequence[_Info]:
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
            if (info := _load_plugin(file_name, base_dir / file_name)) is not None:
                infos.append(info)

    return infos


def _get_free_space() -> int:
    statvfs_result = os.statvfs(omd_root)
    return statvfs_result.f_bavail * statvfs_result.f_frsize


def _delete_file(path: str, reason: str) -> bool:
    try:
        _log(f"Deleting file ({reason}): {path}")
        os.unlink(path)

        # Also delete any .info files which are connected to the RRD file
        if path.endswith(".rrd"):
            path = f"{path[:-3]}info"
            if os.path.exists(path):
                _log(f"Deleting file ({reason}): {path}")
                os.unlink(path)

        return True
    except Exception as e:
        _error(f"Error while deleting {path}: {e}")
    return False


def _delete_files_and_base_directory(path: str, reason: str) -> bool:
    """
    Deletes files in a directory and the directory itself
    (not walk into subdirectories. Failing instead)
    """
    try:
        _log(f"Deleting directory and files ({reason}): {path}")
        for file_name in os.listdir(path):
            os.unlink(path + "/" + file_name)
        os.rmdir(path)
        return True
    except Exception as e:
        _error(f"Error while deleting {path}: {e}")
    return False


def _oldest_candidate(min_file_age: int, path_to_mod_time: Mapping[str, float]) -> str | None:
    if path_to_mod_time:
        # Sort by modification time
        oldest, age = max(path_to_mod_time.items(), key=lambda key_val: key_val[1])
        if age < time.time() - min_file_age:
            return oldest
    return None


def _cleanup_host_directories(
    retention_time: int, unaffected_hosts: set[str], base_path: str
) -> set[str]:
    if not os.path.isdir(base_path):
        return set()

    abandoned = {host_dir for host_dir in os.listdir(base_path) if host_dir not in unaffected_hosts}

    return _check_threshold_and_delete(retention_time, abandoned, base_path)


def _check_threshold_and_delete(
    retention_time: int, abandoned_hosts: set[str], base_path: str
) -> set[str]:
    """
    Find the latest modified file for each directory. When the latest
    modified file is older than the threshold, delete all files including
    the host base directory.
    """
    cleaned_up_hosts = set()
    for unrelated_dir in abandoned_hosts:
        path = f"{base_path}/{unrelated_dir}"
        mtime: float = _newest_modification_time_in_dir(path)
        if mtime < time.time() - retention_time:
            _delete_files_and_base_directory(path, "abandoned host")
            cleaned_up_hosts.add(unrelated_dir)
        else:
            _verbose(f"Found abandoned host path (but not old enough): {path}")

    return cleaned_up_hosts


def _do_automation_call(
    hosts_to_cleanup: set[str],
    automation_call: Literal["delete-hosts", "delete-hosts-known-remote"],
) -> None:
    command: list[str] = ["check_mk", "--automation", automation_call] + list(hosts_to_cleanup)
    _verbose('Calling "{}"'.format(" ".join(command)))
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as p:
        if p.wait() != 0:
            assert p.stdout is not None
            _error(
                'Failed to execute "%s" to cleanup the host files. Exit-Code: %d, Output: %r'
                % (" ".join(command), p.returncode, p.stdout.read())
            )


def _newest_modification_time_in_dir(dir_path: str) -> float:
    mtime: float = 0.0
    for entry in os.listdir(dir_path):
        path = dir_path + "/" + entry
        mtime = max(os.stat(path).st_mtime, mtime)
    return mtime


def _do_cleanup_central_site(retention_time: int, local_site_hosts: set[str]) -> None:
    try:
        all_hosts = set(
            subprocess.check_output(
                ["check_mk", "--list-hosts", "--all-sites", "--include-offline"],
                encoding="utf-8",
            ).splitlines()
        )
    except subprocess.CalledProcessError as e:
        _verbose(f"Failed to get site hosts ({e}). Skipping abandoned host files cleanup")
        return

    cleaned_up = (
        _cleanup_host_directories(
            retention_time,
            all_hosts,
            f"{var_dir}/inventory_archive",
        )
        | _cleanup_host_directories(
            retention_time,
            local_site_hosts,
            f"{omd_root}/var/pnp4nagios/perfdata",
        )
        | _cleanup_host_directories(
            retention_time,
            local_site_hosts,
            f"{var_dir}/rrd",
        )
    )

    if cleaned_up_deleted_hosts := cleaned_up - all_hosts:
        _do_automation_call(cleaned_up_deleted_hosts, "delete-hosts")
    if cleaned_up_remote_hosts := cleaned_up & (all_hosts - local_site_hosts):
        _do_automation_call(cleaned_up_remote_hosts, "delete-hosts-known-remote")


def _do_cleanup_remote_site(retention_time: int, local_site_hosts: set[str]) -> None:
    cleaned_up_non_local_hosts = (
        _cleanup_host_directories(
            retention_time,
            local_site_hosts,
            f"{var_dir}/inventory_archive",
        )
        | _cleanup_host_directories(
            retention_time,
            local_site_hosts,
            f"{omd_root}/var/pnp4nagios/perfdata",
        )
        | _cleanup_host_directories(
            retention_time,
            local_site_hosts,
            f"{var_dir}/rrd",
        )
    )

    if cleaned_up_non_local_hosts:
        _do_automation_call(cleaned_up_non_local_hosts, "delete-hosts")


def _do_cleanup_abandoned_host_files(cleanup_abandoned_host_files: int | None) -> None:
    if not cleanup_abandoned_host_files:
        return

    is_wato_remote_site = get_site_distributed_setup() == SiteDistributedSetup.DISTRIBUTED_REMOTE

    try:
        local_site_hosts = set(
            subprocess.check_output(
                ["check_mk", "--list-hosts", "--include-offline"], encoding="utf-8"
            ).splitlines()
        )
    except subprocess.CalledProcessError as e:
        _verbose(f"Failed to get site hosts ({e}). Skipping abandoned host files cleanup")
        return

    if not local_site_hosts:
        _verbose("Found no hosts. Be careful and not cleaning up anything.")
        return

    if is_wato_remote_site:
        _do_cleanup_remote_site(cleanup_abandoned_host_files, local_site_hosts)
    else:
        _do_cleanup_central_site(cleanup_abandoned_host_files, local_site_hosts)


def _cleanup_aged(max_file_age: int | None, infos: Sequence[_Info]) -> None:
    """
    Loop all files to check whether files are older than
    max_age. Simply remove all of them.

    """
    if max_file_age is None:
        _verbose("Not cleaning up too old files (not enabled)")
        return
    max_age: float = time.time() - max_file_age

    for info in infos:
        for path, mtime in info.path_to_mod_time.items():
            if mtime < max_age:
                _delete_file(path, "too old")
            else:
                _verbose(f"Not deleting {path}")

    bytes_free: int = _get_free_space()
    _verbose(f"Free space (after file age cleanup): {fmt_bytes(bytes_free)}")


def _cleanup_oldest_files(
    force: bool,
    min_free_bytes_and_age: tuple[int, int] | None,
    infos: Sequence[_Info],
) -> None:
    if min_free_bytes_and_age is None:
        _verbose("Not cleaning up oldest files of plugins (not enabled)")
        return
    min_free_bytes, min_file_age = min_free_bytes_and_age

    # check disk space against configuration
    bytes_free: int = _get_free_space()
    if not force and bytes_free >= min_free_bytes:
        _verbose(
            f"Free space is above threshold of {fmt_bytes(min_free_bytes)}. Nothing to be done."
        )
        return

    # the scheduling of the cleanup job is supposed to be equal for
    # all sites. To ensure that not only one single site is always
    # cleaning up, we add a random wait before cleanup.
    sleep_sec = float(random.randint(0, 10000)) / 1000
    _verbose(f"Sleeping for {sleep_sec:0.3f} seconds")
    time.sleep(sleep_sec)

    # Loop all cleanup plugins to find the oldest candidate per plugin
    # which is older than min_age and delete this file.
    for info in infos:
        oldest = _oldest_candidate(min_file_age, info.path_to_mod_time)
        if oldest is not None and os.path.exists(oldest):  # _cleanup_aged might have deleted oldest
            _delete_file(oldest, info.plugin_name + ": my oldest")

    bytes_free = _get_free_space()
    _verbose(f"Free space (after min free space space cleanup): {fmt_bytes(bytes_free)}")


def main() -> None:
    _setup_logging("-v" in sys.argv)
    config = read_config(diskspace_config_dir)
    _print_config(config)
    infos = _load_plugins(omd_root / "share/diskspace", omd_root / "local/share/diskspace")

    _do_cleanup_abandoned_host_files(config.cleanup_abandoned_host_files)

    # get used disk space of the sites volume
    bytes_free = _get_free_space()
    _verbose(f"Free space: {fmt_bytes(bytes_free)}")

    _cleanup_aged(config.max_file_age, infos)
    _cleanup_oldest_files("-f" in sys.argv, config.min_free_bytes, infos)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _error(f"Unexpected exception: {traceback.format_exc()}")
        sys.exit(1)
