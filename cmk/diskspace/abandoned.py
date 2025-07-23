#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
import time
from pathlib import Path
from typing import Literal

from cmk.diskspace.logging import error, log, verbose


def _delete_files_and_base_directory(path: str, reason: str) -> bool:
    """
    Deletes files in a directory and the directory itself
    (not walk into subdirectories. Failing instead)
    """
    try:
        log(f"Deleting directory and files ({reason}): {path}")
        for file_name in os.listdir(path):
            os.unlink(path + "/" + file_name)
        os.rmdir(path)
        return True
    except Exception as e:
        error(f"Error while deleting {path}: {e}")
    return False


def _newest_modification_time_in_dir(dir_path: str) -> float:
    mtime: float = 0.0
    for entry in os.listdir(dir_path):
        path = dir_path + "/" + entry
        mtime = max(os.stat(path).st_mtime, mtime)
    return mtime


def _check_threshold_and_delete(
    now: float, retention_time: int, abandoned_hosts: set[str], base_path: str
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
        if mtime < now - retention_time:
            _delete_files_and_base_directory(path, "abandoned host")
            cleaned_up_hosts.add(unrelated_dir)
        else:
            verbose(f"Found abandoned host path (but not old enough): {path}")

    return cleaned_up_hosts


def _cleanup_host_directories(
    now: float, retention_time: int, unaffected_hosts: set[str], base_path: str
) -> set[str]:
    if not os.path.isdir(base_path):
        return set()

    abandoned = {host_dir for host_dir in os.listdir(base_path) if host_dir not in unaffected_hosts}

    return _check_threshold_and_delete(now, retention_time, abandoned, base_path)


def _do_automation_call(
    hosts_to_cleanup: set[str],
    automation_call: Literal["delete-hosts", "delete-hosts-known-remote"],
) -> None:
    command: list[str] = ["check_mk", "--automation", automation_call] + list(hosts_to_cleanup)
    verbose('Calling "{}"'.format(" ".join(command)))
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as p:
        if p.wait() != 0:
            assert p.stdout is not None
            error(
                'Failed to execute "%s" to cleanup the host files. Exit-Code: %d, Output: %r'
                % (" ".join(command), p.returncode, p.stdout.read())
            )


def _do_cleanup_central_site(
    omd_root: Path, retention_time: int, local_site_hosts: set[str]
) -> None:
    try:
        all_hosts = set(
            subprocess.check_output(
                ["check_mk", "--list-hosts", "--all-sites", "--include-offline"],
                encoding="utf-8",
            ).splitlines()
        )
    except subprocess.CalledProcessError as e:
        verbose(f"Failed to get site hosts ({e}). Skipping abandoned host files cleanup")
        return

    cleaned_up = (
        _cleanup_host_directories(
            time.time(),
            retention_time,
            all_hosts,
            f"{omd_root}/var/check_mk/inventory_archive",
        )
        | _cleanup_host_directories(
            time.time(),
            retention_time,
            local_site_hosts,
            f"{omd_root}/var/pnp4nagios/perfdata",
        )
        | _cleanup_host_directories(
            time.time(),
            retention_time,
            local_site_hosts,
            f"{omd_root}/var/check_mk/rrd",
        )
    )

    # The invocation `cmk-update-agent register --hostname myhost ...` will unconditionally create
    # these files, and they can be used afterwards by creating the host. So, a user might first do
    # the registration and then the site configuration. However, its is unlikely this file is useful
    # after more than a day.
    # Note: All these files only exist on the central site. If a host is deleted, then these files
    # are deleted via the `delete-host` automation. If a host is moved between sites, then these
    # files remain where they are, so diskspace does not need special logic for those cases.
    _cleanup_host_directories(
        time.time(),
        retention_time,
        all_hosts,
        f"{omd_root}/var/check_mk/agent_deployment/",
    )

    if cleaned_up_deleted_hosts := cleaned_up - all_hosts:
        _do_automation_call(cleaned_up_deleted_hosts, "delete-hosts")
    if cleaned_up_remote_hosts := cleaned_up & (all_hosts - local_site_hosts):
        _do_automation_call(cleaned_up_remote_hosts, "delete-hosts-known-remote")


def _do_cleanup_remote_site(
    omd_root: Path, retention_time: int, local_site_hosts: set[str]
) -> None:
    cleaned_up_non_local_hosts = (
        _cleanup_host_directories(
            time.time(),
            retention_time,
            local_site_hosts,
            f"{omd_root}/var/check_mk/inventory_archive",
        )
        | _cleanup_host_directories(
            time.time(),
            retention_time,
            local_site_hosts,
            f"{omd_root}/var/pnp4nagios/perfdata",
        )
        | _cleanup_host_directories(
            time.time(),
            retention_time,
            local_site_hosts,
            f"{omd_root}/var/check_mk/rrd",
        )
    )

    if cleaned_up_non_local_hosts:
        _do_automation_call(cleaned_up_non_local_hosts, "delete-hosts")


def do_cleanup_abandoned_host_files(
    omd_root: Path, is_wato_remote_site: bool, cleanup_abandoned_host_files: int
) -> None:
    try:
        local_site_hosts = set(
            subprocess.check_output(
                ["check_mk", "--list-hosts", "--include-offline"], encoding="utf-8"
            ).splitlines()
        )
    except subprocess.CalledProcessError as e:
        verbose(f"Failed to get site hosts ({e}). Skipping abandoned host files cleanup")
        return

    if not local_site_hosts:
        verbose("Found no hosts. Be careful and not cleaning up anything.")
        return

    if is_wato_remote_site:
        _do_cleanup_remote_site(omd_root, cleanup_abandoned_host_files, local_site_hosts)
    else:
        _do_cleanup_central_site(omd_root, cleanup_abandoned_host_files, local_site_hosts)
