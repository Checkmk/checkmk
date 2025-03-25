#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helper functions for dealing with the tmpfs"""

import errno
import os
import re
import shlex
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from omdlib.console import ok
from omdlib.contexts import SiteContext
from omdlib.utils import (
    chown_tree,
    create_skeleton_files,
    delete_directory_contents,
    is_containerized,
)
from omdlib.version_info import VersionInfo

import cmk.utils.tty as tty


# TODO: Use site context?
def tmpfs_mounted(sitename: str) -> bool:
    # Problem here: if /omd is a symbolic link somewhere else,
    # then in /proc/mounts the physical path will appear and be
    # different from tmp_path. We just check the suffix therefore.
    path_suffix = "sites/%s/tmp" % sitename
    with Path("/proc/mounts").open() as mounts:
        for line in mounts:
            try:
                _device, mp, fstype, _options, _dump, _fsck = line.split()
                if mp.endswith(path_suffix) and fstype == "tmpfs":
                    return True
            except Exception:
                continue
    return False


def prepare_tmpfs(version_info: VersionInfo, site_name: str, tmp_dir: str, tmpfs_hook: str) -> None:
    if tmpfs_mounted(site_name):
        sys.stdout.write("Temporary filesystem already mounted\n")
        return  # Fine: Mounted

    if tmpfs_hook != "on":
        sys.stdout.write("Preparing tmp directory %s..." % tmp_dir)
        sys.stdout.flush()

        if os.path.exists(tmp_dir):
            return

        try:
            os.mkdir(tmp_dir)
            os.chmod(tmp_dir, 0o751)  # nosec B103 # BNS:7e6b08
        except OSError as e:
            if e.errno != errno.EEXIST:  # File exists
                raise
        return

    sys.stdout.write("Creating temporary filesystem %s..." % tmp_dir)
    sys.stdout.flush()
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
        os.chmod(tmp_dir, 0o751)  # nosec B103 # BNS:7e6b08

    mount_options = shlex.split(version_info.MOUNT_OPTIONS)
    completed_process = subprocess.run(
        ["mount"] + mount_options + [tmp_dir],
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        check=False,
    )
    if completed_process.returncode == 0:
        ok()
        return  # Fine: Mounted

    sys.stdout.write(completed_process.stdout)
    if is_containerized():
        sys.stdout.write(
            tty.warn + ": "
            "Could not mount tmpfs. You may either start the container in "
            'privileged mode or use the "docker run" option "--tmpfs" to '
            "make docker do the tmpfs mount for the site.\n"
        )

    sys.stdout.write(
        tty.warn + ": You may continue without tmpfs, but the "
        "performance of Check_MK may be degraded.\n"
    )


def mark_tmpfs_initialized(site: SiteContext) -> None:
    """Write a simple file marking the time of the tmpfs structure initialization

    The st_ctime of the file will be used by Checkmk to know when the tmpfs file
    structure was initialized."""
    with Path(site.tmp_dir, "initialized").open("w", encoding="utf-8") as f:
        f.write("")


def unmount_tmpfs(site: SiteContext, output: bool = True, kill: bool = False) -> bool:
    # During omd update TMPFS hook might not be set so assume
    # that the hook is enabled by default.
    # If kill is True, then we do an fuser -k on the tmp
    # directory first.

    # For some files in tmpfs we want the IO performance of the tmpfs and
    # want to keep the files between unmount / mount operations (if possible).
    if tmpfs_mounted(site.name):
        if output:
            sys.stdout.write("Saving temporary filesystem contents...")
        save_tmpfs_dump(site)
        if output:
            ok()
    return unmount_tmpfs_without_save(site.name, site.tmp_dir, output, kill)


def unmount_tmpfs_without_save(  # pylint: disable=too-many-branches
    site_name: str,
    tmp_dir: str,
    output: bool,
    kill: bool,
) -> bool:
    # Clear directory hierarchy when not using a tmpfs
    if not tmpfs_mounted(site_name) or _tmpfs_is_managed_by_node(site_name, tmp_dir):
        tmp = tmp_dir
        if os.path.exists(tmp):
            if output:
                sys.stdout.write("Cleaning up tmp directory...")
                sys.stdout.flush()
            delete_directory_contents(tmp)
            if output:
                ok()
        return True

    if output:
        sys.stdout.write("Unmounting temporary filesystem...")

    for _t in range(0, 10):
        if not tmpfs_mounted(site_name):
            if output:
                ok()
            return True

        if _unmount(tmp_dir):
            if output:
                ok()
            return True

        if kill:
            if output:
                sys.stdout.write("Killing processes still using '%s'\n" % tmp_dir)
            subprocess.call(["fuser", "--silent", "-k", tmp_dir])

        if output:
            sys.stdout.write(kill and "K" or ".")
            sys.stdout.flush()
        time.sleep(1)

    if output:
        raise SystemExit(tty.error + ": Cannot unmount temporary filesystem.")

    return False


# Extracted to separate function to be able to monkeypatch the path for tests
def fstab_path() -> Path:
    return Path("/etc/fstab")


def _unmount(tmp_dir: str) -> bool:
    return subprocess.call(["umount", tmp_dir]) == 0


def _tmpfs_is_managed_by_node(site_name: str, tmp_dir: str) -> bool:
    """When running in a container, and the tmpfs is managed by the node, the
    mount is visible, but can not be unmounted. umount exits with 32 in this
    case. Treat this case like there is no tmpfs and only the directory needs
    to be cleaned."""
    if not is_containerized():
        return False

    if not tmpfs_mounted(site_name):
        return False

    return subprocess.call(
        ["umount", tmp_dir], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    ) in [1, 32]


def add_to_fstab(site: SiteContext, tmpfs_size: str | None = None) -> None:
    if not (path_fstab := fstab_path()).exists():
        return  # Don't do anything in case there is no fstab

    # tmpfs                   /opt/omd/sites/b01/tmp  tmpfs   user,uid=b01,gid=b01 0 0
    mountpoint = site.real_tmp_dir
    sys.stdout.write(f"Adding {mountpoint} to {path_fstab}.\n")

    # No size option: using up to 50% of the RAM
    sizespec = ""
    if tmpfs_size is not None and re.match("^[0-9]+(G|M|%)$", tmpfs_size):
        sizespec = ",size=%s" % tmpfs_size

    # Ensure the fstab has a newline char at it's end before appending
    previous_fstab = path_fstab.read_text()
    complete_last_line = previous_fstab and not previous_fstab.endswith("\n")

    with path_fstab.open(mode="a+") as fstab:
        if complete_last_line:
            fstab.write("\n")

        fstab.write(
            f"tmpfs  {mountpoint} tmpfs noauto,user,mode=751,uid={site.name},gid={site.name}{sizespec} 0 0\n"
        )


def remove_from_fstab(site: SiteContext) -> None:
    if not (path_fstab := fstab_path()).exists():
        return  # Don't do anything in case there is no fstab

    mountpoint = site.tmp_dir
    sys.stdout.write(f"Removing {mountpoint} from {path_fstab}...")

    with (
        (path_new_fstab := Path(str(path_fstab) + ".new")).open(mode="w") as newtab,
        path_fstab.open() as current_fstab,
    ):
        for line in current_fstab:
            if "uid=%s," % site.name in line and mountpoint in line:
                continue
            newtab.write(line)
    path_new_fstab.rename(path_fstab)
    ok()


def save_tmpfs_dump(site: SiteContext) -> None:
    """Dump tmpfs content for later restore after remount

    Creates a tar archive from the current tmpfs contents that is restored to the
    tmpfs later after mounting it again.

    Please note that this only preserves specific files, not the whole tmpfs.
    """
    save_paths = [
        Path(site.tmp_dir) / "check_mk" / "piggyback",
        Path(site.tmp_dir) / "check_mk" / "piggyback_sources",
        Path(site.tmp_dir) / "check_mk" / "counters",
    ]

    dump_path = _tmpfs_dump_path(site)
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.TarFile(dump_path, mode="w") as f:
        for save_path in save_paths:
            if save_path.exists():
                f.add(str(save_path), arcname=str(save_path.relative_to(site.tmp_dir)))
    assert dump_path.exists()


def restore_tmpfs_dump(site: SiteContext) -> None:
    """Populate the tmpfs from the previously created tmpfs dump
    Silently skipping over in case there is no dump available."""
    if not _tmpfs_dump_path(site).exists():
        return
    with tarfile.TarFile(_tmpfs_dump_path(site)) as tar:
        tar.extractall(site.tmp_dir, filter="data")  # nosec B202 # BNS:a7d6b8
    _tmpfs_dump_path(site).unlink()


def _tmpfs_dump_path(site: SiteContext) -> Path:
    return Path(site.dir, "var", "omd", "tmpfs-dump.tar")


def prepare_and_populate_tmpfs(version_info: VersionInfo, site: SiteContext, skelroot: str) -> None:
    prepare_tmpfs(version_info, site.name, site.tmp_dir, site.conf["TMPFS"])

    if not os.listdir(site.tmp_dir):
        create_skeleton_files(site.dir, site.replacements(), skelroot, site.skel_permissions, "tmp")
        chown_tree(site.tmp_dir, site.name)
        mark_tmpfs_initialized(site)
        restore_tmpfs_dump(site)

    _create_livestatus_tcp_socket_link(site)


def _create_livestatus_tcp_socket_link(site: SiteContext) -> None:
    """Point the xinetd to the livestatus socket inteded by LIVESTATUS_TCP_TLS"""
    link_path = site.tmp_dir + "/run/live-tcp"
    target = "live-tls" if site.conf["LIVESTATUS_TCP_TLS"] == "on" else "live"

    if os.path.lexists(link_path):
        os.unlink(link_path)

    parent_dir = os.path.dirname(link_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    os.symlink(target, link_path)
