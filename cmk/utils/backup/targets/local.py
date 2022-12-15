#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import os
import shutil
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from cmk.utils.backup.type_defs import Backup, Job, JobConfig, SiteBackupInfo, TargetId
from cmk.utils.backup.utils import (
    current_site_id,
    load_backup_info,
    log,
    makedirs,
    save_backup_info,
    UnrecognizedBackupTypeError,
    verify_backup_file,
)
from cmk.utils.exceptions import MKGeneralException


def archive_suffix(config: JobConfig) -> str:
    suffix = ".tar"
    if config["compress"]:
        suffix += ".gz"
    if config["encrypt"]:
        suffix += ".enc"
    return suffix


class LocalTarget:
    def __init__(self, target_id: TargetId, params: Mapping[str, Any]) -> None:
        self.id = target_id
        self.path = Path(params["path"])
        self.is_mountpoint = bool(params["is_mountpoint"])

    def check_ready(self) -> None:
        if not self.path.exists():
            raise MKGeneralException(f"Local target path does not exist: {self.path}")
        if self.is_mountpoint and not os.path.ismount(self.path):
            raise MKGeneralException(
                "The backup target path is configured to be a mountpoint, but nothing is mounted."
            )

    def list_backups(self) -> Iterator[tuple[str, SiteBackupInfo]]:
        for backup_id in self.path.iterdir():
            # if backup_id is a directory not owned by the current user
            # any attempt to get information about files in the folder will
            # result in a permission error. In that case do not show a backup
            try:
                if backup_id.is_dir() and (backup_id / "mkbackup.info").exists():
                    try:
                        yield backup_id.name, load_backup_info(backup_id / "mkbackup.info")
                    except UnrecognizedBackupTypeError:
                        continue
            except PermissionError:
                continue

    def get_backup(self, backup_id: str) -> Backup:
        backup_path = self.path / backup_id
        info_path = backup_path / "mkbackup.info"
        if not backup_path.exists() or not info_path.exists():
            raise MKGeneralException(
                f"This backup does not exist (Use 'mkbackup list {self.id}' to "
                "show a list of available backups)."
            )
        info = load_backup_info(info_path)
        archive_file = backup_path / info.filename
        verify_backup_file(info, archive_file)
        return Backup(info, backup_id, archive_file)

    def _working_dir(self, job: Job) -> Path:
        return self.path / f"{job.id}-incomplete"

    def start_backup(self, job: Job) -> Path:
        site = current_site_id()
        working_dir = self._working_dir(job)
        if working_dir.exists():
            try:
                shutil.rmtree(working_dir)
            except OSError as e:
                if e.errno == errno.EACCES:
                    raise MKGeneralException(f"Failed to write the backup directory: {working_dir}")
                raise
        path = working_dir / f"site-{site}{archive_suffix(job.config)}"
        makedirs(path.parent, group="omd", mode=0o775)
        return path

    def finish_backup(self, info: SiteBackupInfo, job: Job) -> None:
        save_backup_info(info, self._working_dir(job) / "mkbackup.info")
        completed_path = self.path / f"{job.id}-complete"
        if completed_path.exists():
            log("Cleaning up previously completed backup")
            shutil.rmtree(completed_path)
        os.rename(self._working_dir(job), completed_path)
