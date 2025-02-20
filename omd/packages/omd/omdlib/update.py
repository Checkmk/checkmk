#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow-any-expr

import contextlib
import enum
import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Literal, Self

from omdlib.contexts import SiteContext
from omdlib.tmpfs import prepare_and_populate_tmpfs, unmount_tmpfs_without_save
from omdlib.version_info import VersionInfo


def store(site_dir: Path, relpath: Path | str, backup_dir: Path) -> None:
    # `store` is only valid on files, symlinks and empty dirs.
    source = site_dir / relpath
    destination = backup_dir / relpath
    match file_type(source):
        case ManagedTypes.file:
            shutil.copy2(source, destination)
        case ManagedTypes.symlink:
            destination.symlink_to(source.readlink())
        case ManagedTypes.directory:
            destination.mkdir()
            shutil.copystat(source, destination)
        case ManagedTypes.missing:
            pass
        case ManagedTypes.unknown:
            raise NotImplementedError()


def restore(site_dir: Path, relpath: Path | str, backup_dir: Path) -> None:
    source = backup_dir / relpath
    destination = site_dir / relpath
    match file_type(source):
        case ManagedTypes.file:
            shutil.copy2(source, destination)
        case ManagedTypes.symlink:
            destination.unlink(missing_ok=True)
            destination.symlink_to(source.readlink())
        case ManagedTypes.directory:
            destination.mkdir(exist_ok=True)
            shutil.copystat(source, destination)
        case ManagedTypes.missing:
            if destination.is_dir():
                destination.rmdir()
            elif destination.is_file() or destination.is_symlink():
                destination.unlink(missing_ok=True)
        case ManagedTypes.unknown:
            raise Exception()


class ManagedTypes(enum.Enum):
    missing = "missing"
    file = "file"
    symlink = "symlink"
    directory = "directory"
    unknown = "unknown"


def file_type(path: Path) -> ManagedTypes:
    if not path.exists(follow_symlinks=False):
        return ManagedTypes.missing
    if path.is_symlink():
        return ManagedTypes.symlink
    if path.is_file():
        return ManagedTypes.file
    if path.is_dir():
        return ManagedTypes.directory
    return ManagedTypes.unknown


####


def walk_in_DFS_order(path: Path) -> Iterator[Path]:
    for root, _directories, files in os.walk(path):
        yield Path(root)
        for file in files:
            yield Path(root).joinpath(file)


def walk_managed(site_dir: Path, skel: Path) -> Iterator[str]:
    for path in walk_in_DFS_order(skel):
        relpath = os.path.relpath(path, start=skel)
        yield relpath


def backup_managed(site_dir: Path, old_skel: Path, new_skel: Path, backup_dir: Path) -> None:
    for relpath in walk_managed(site_dir, new_skel):
        store(site_dir, Path(relpath), backup_dir)
    for relpath in walk_managed(site_dir, old_skel):
        if not os.path.lexists(new_skel / relpath):  # Already backed-up
            store(site_dir, Path(relpath), backup_dir)


def restore_managed(site_dir: Path, old_skel: Path, new_skel: Path, backup_dir: Path) -> None:
    for relpath in walk_managed(site_dir, old_skel):
        if not (new_skel / relpath).exists():
            restore(site_dir, Path(relpath), backup_dir)
    for relpath in reversed(list(walk_managed(site_dir, new_skel))):
        restore(site_dir, Path(relpath), backup_dir)


def _store_version_meta_dir(site_dir: Path, backup_dir: Path) -> None:
    version_meta_dir = site_dir / ".version_meta"
    if version_meta_dir.exists():
        shutil.copytree(version_meta_dir, backup_dir / ".version_meta", symlinks=True)


def _restore_version_meta_dir(site_dir: Path, backup_dir: Path) -> None:
    version_meta_dir = site_dir / ".version_meta"
    backup_version_meta_dir = backup_dir / ".version_meta"
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(version_meta_dir)
    if backup_version_meta_dir.exists():
        shutil.copytree(backup_version_meta_dir, version_meta_dir, symlinks=True)


HOOK_RELPATHS = [
    "etc/check_mk/multisite.d/liveproxyd.mk",
    "etc/apache/apache/listen-port.conf",
    "etc/mk-livestatus/xinetd.conf",
    "etc/xinetd.d/mk-livestatus",
    "etc/apache/conf.d/nagios.conf",
    "etc/check_mk/conf.d/microcore.mk",
    "var/log/livestatus.log",
    "var/log/nagios.log",
    "etc/init.d/core",
    "var/check_mk/core/config",
    ".forward",
    "etc/mod-gearman/perfdata.conf",
    "etc/nagios/nagios.d/pnp4nagios.cfg",
    "etc/apache/conf.d/pnp4nagios.conf",
    "etc/check_mk/conf.d/pnp4nagios.mk",
    "etc/apache/conf.d/cookie_auth.conf",
    "etc/nagvis/conf.d/cookie_auth.ini.php",
    "etc/pnp4nagios/config.d/cookie_auth.php",
    "etc/check_mk/multisite.d/mkeventd.mk",
    "etc/check_mk/conf.d/mkeventd.mk",
    "etc/omd/site.conf",
]


class ManageUpdate:
    def __init__(
        self,
        site_name: str,
        tmp_dir: str,
        site_dir: Path,
        old_skel: Path,
        new_skel: Path,
    ) -> None:
        self.backup_dir = site_dir / ".update_backup"
        self.old_skel = old_skel
        self.new_skel = new_skel
        self.site_dir = site_dir
        self.site_name = site_name
        self.tmp_dir = tmp_dir
        self.populated_tmpfs = False

    def __enter__(self) -> Self:
        if self.backup_dir.exists():
            sys.exit(
                f"The folder {self.backup_dir} contains data from a failed update attempt. This "
                "only happens, if a serious error occured during a previous update attempt. "
                f"Please contact support. "
                "Since the root cause of this error is not known to OMD, the site is an "
                "unknown state and both, restarting or updating the site, can have unknown effects.\n"
            )
        backup_managed(self.site_dir, self.old_skel, self.new_skel, self.backup_dir)
        store(self.site_dir, "version", self.backup_dir)
        _store_version_meta_dir(self.site_dir, self.backup_dir)
        for relpath in HOOK_RELPATHS:
            store(self.site_dir, relpath, self.backup_dir)
        return self

    def prepare_and_populate_tmpfs(self, version: VersionInfo, site: SiteContext) -> None:
        prepare_and_populate_tmpfs(version, site, str(self.new_skel))
        self.populated_tmpfs = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        if exc_type is not None:
            if self.populated_tmpfs:
                # Always leave the tmpfs unmounted. We currently are in the context of the new
                # version (symlink has been restored, but python3 interpreter and dynamic libraries
                # are pointing to the new context. Thus, we only umount here.
                unmount_tmpfs_without_save(self.site_name, self.tmp_dir, False, False)
            for relpath in HOOK_RELPATHS:
                restore(self.site_dir, relpath, self.backup_dir)
            _restore_version_meta_dir(self.site_dir, self.backup_dir)
            restore(self.site_dir, "version", self.backup_dir)
            restore_managed(self.site_dir, self.old_skel, self.new_skel, self.backup_dir)
        shutil.rmtree(self.backup_dir)
        return False  # Don't suppress the exception
