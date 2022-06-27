#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
#       U  ___ u  __  __   ____
#        \/"_ \/U|' \/ '|u|  _"\
#        | | | |\| |\/| |/| | | |
#    .-,_| |_| | | |  | |U| |_| |\
#     \_)-\___/  |_|  |_| |____/ u
#          \\   <<,-,,-.   |||_
#         (__)   (./  \.) (__)_)
#
# This file is part of OMD - The Open Monitoring Distribution.
# The official homepage is at <http://omdistro.org>.
#
# OMD  is  free software;  you  can  redistribute it  and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the  Free Software  Foundation  in  version 2.  OMD  is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
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
from typing import Optional

from omdlib.console import ok
from omdlib.contexts import SiteContext
from omdlib.utils import delete_directory_contents, is_dockerized
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


def prepare_tmpfs(version_info: VersionInfo, site: SiteContext) -> None:
    if tmpfs_mounted(site.name):
        sys.stdout.write("Temporary filesystem already mounted\n")
        return  # Fine: Mounted

    if site.conf["TMPFS"] != "on":
        sys.stdout.write("Preparing tmp directory %s..." % site.tmp_dir)
        sys.stdout.flush()

        if os.path.exists(site.tmp_dir):
            return

        try:
            os.mkdir(site.tmp_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:  # File exists
                raise
        return

    sys.stdout.write("Creating temporary filesystem %s..." % site.tmp_dir)
    sys.stdout.flush()
    if not os.path.exists(site.tmp_dir):
        os.mkdir(site.tmp_dir)

    mount_options = shlex.split(version_info.MOUNT_OPTIONS)
    completed_process = subprocess.run(
        ["mount"] + mount_options + [site.tmp_dir],
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
    if is_dockerized():
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


def unmount_tmpfs(  # pylint: disable=too-many-branches
    site: SiteContext,
    output: bool = True,
    kill: bool = False,
) -> bool:
    # During omd update TMPFS hook might not be set so assume
    # that the hook is enabled by default.
    # If kill is True, then we do an fuser -k on the tmp
    # directory first.

    # For some files in tmpfs we want the IO performance of the tmpfs and
    # want to keep the files between unmount / mount operations (if possible).
    if os.path.exists(site.tmp_dir):
        if output:
            sys.stdout.write("Saving temporary filesystem contents...")
        save_tmpfs_dump(site)
        if output:
            ok()

    # Clear directory hierarchy when not using a tmpfs
    if not tmpfs_mounted(site.name) or _tmpfs_is_managed_by_node(site):
        tmp = site.tmp_dir
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
        if not tmpfs_mounted(site.name):
            if output:
                ok()
            return True

        if _unmount(site):
            if output:
                ok()
            return True

        if kill:
            if output:
                sys.stdout.write("Killing processes still using '%s'\n" % site.tmp_dir)
            subprocess.call(["fuser", "--silent", "-k", site.tmp_dir])

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


def _unmount(site: SiteContext) -> bool:
    return subprocess.call(["umount", site.tmp_dir]) == 0


def _tmpfs_is_managed_by_node(site: SiteContext) -> bool:
    """When running in a container, and the tmpfs is managed by the node, the
    mount is visible, but can not be unmounted. umount exits with 32 in this
    case. Treat this case like there is no tmpfs and only the directory needs
    to be cleaned."""
    if not is_dockerized():
        return False

    if not tmpfs_mounted(site.name):
        return False

    return subprocess.call(
        ["umount", site.tmp_dir], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    ) in [1, 32]


def add_to_fstab(site: SiteContext, tmpfs_size: Optional[str] = None) -> None:
    if not (path_fstab := fstab_path()).exists():
        return  # Don't do anything in case there is no fstab

    # tmpfs                   /opt/omd/sites/b01/tmp  tmpfs   user,uid=b01,gid=b01 0 0
    mountpoint = site.real_tmp_dir
    sys.stdout.write("Adding %s to %s.\n" % (mountpoint, path_fstab))

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
            "tmpfs  %s tmpfs noauto,user,mode=755,uid=%s,gid=%s%s 0 0\n"
            % (mountpoint, site.name, site.name, sizespec)
        )


def remove_from_fstab(site: SiteContext) -> None:
    if not (path_fstab := fstab_path()).exists():
        return  # Don't do anything in case there is no fstab

    mountpoint = site.tmp_dir
    sys.stdout.write(f"Removing {mountpoint} from {path_fstab}...")

    with (path_new_fstab := Path(str(path_fstab) + ".new")).open(
        mode="w"
    ) as newtab, path_fstab.open() as current_fstab:
        for line in current_fstab:
            if "uid=%s," % site.name in line and mountpoint in line:
                continue
            newtab.write(line)
    path_new_fstab.rename(path_fstab)
    ok()


def save_tmpfs_dump(site):
    # type: (SiteContext) -> None
    """Dump tmpfs content for later restore after remount

    Creates a tar archive from the current tmpfs contents that is restored to the
    tmpfs later after mounting it again.

    Please note that this only preserves specific files, not the whole tmpfs.
    """
    save_paths = [
        Path(site.tmp_dir) / "check_mk" / "piggyback",
        Path(site.tmp_dir) / "check_mk" / "piggyback_sources",
    ]

    dump_path = _tmpfs_dump_path(site)
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.TarFile(dump_path, mode="w") as f:
        for save_path in save_paths:
            if save_path.exists():
                f.add(str(save_path), arcname=str(save_path.relative_to(site.tmp_dir)))
    assert dump_path.exists()


def restore_tmpfs_dump(site):
    # type: (SiteContext) -> None
    """Populate the tmpfs from the previously created tmpfs dump
    Silently skipping over in case there is no dump available."""
    if not _tmpfs_dump_path(site).exists():
        return
    with tarfile.TarFile(_tmpfs_dump_path(site)) as tar:
        tar.extractall(site.tmp_dir)


def _tmpfs_dump_path(site):
    # type: (SiteContext) -> Path
    return Path(site.dir, "var", "omd", "tmpfs-dump.tar")
