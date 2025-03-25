#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Final, Generic, Protocol, TypedDict, TypeVar

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.backup.targets.local import LocalTarget
from cmk.utils.backup.type_defs import Backup, SiteBackupInfo
from cmk.utils.backup.utils import (
    BACKUP_INFO_FILENAME,
    load_backup_info,
    log,
    UnrecognizedBackupTypeError,
    verify_backup_file,
)

from ..job import Job
from . import TargetId
from .local import LocalTargetParams

TRemoteParams = TypeVar("TRemoteParams", bound=Mapping[str, object])


class RemoteTargetParams(TypedDict, Generic[TRemoteParams]):
    remote: TRemoteParams
    temp_folder: LocalTargetParams


class RemoteStorage(Protocol):
    def __init__(self, params: Mapping[str, object]) -> None: ...

    def ready(self) -> None: ...

    def download(self, key: Path, tmp: Path) -> Path: ...

    def upload(self, file: Path, key: Path) -> None: ...

    def remove(self, key: Path) -> None: ...

    def objects(self) -> Iterator[Path]: ...


TRemoteStorage = TypeVar("TRemoteStorage", bound=RemoteStorage)


class RemoteTarget(ABC, Generic[TRemoteParams, TRemoteStorage]):
    def __init__(self, target_id: TargetId, params: RemoteTargetParams[TRemoteParams]) -> None:
        self.id: Final = target_id
        self.local_target: Final = LocalTarget(self.id, params["temp_folder"])
        self.remote_storage: Final = self._remote_storage(params["remote"])

    @staticmethod
    @abstractmethod
    def _remote_storage(remote_params: TRemoteParams) -> TRemoteStorage: ...

    def check_ready(self) -> None:
        self.local_target.check_ready()
        self.remote_storage.ready()

    def _get_file(self, key: Path) -> Path:
        try:
            log(f"Downloading {key} from remote storage to {self.local_target.path}")
            return self.remote_storage.download(key, self.local_target.path)
        except Exception as e:
            raise MKGeneralException(
                f"Download of {key} to {self.local_target.path} failed. Original error: {e}"
            )

    def list_backups(self) -> Iterator[tuple[str, SiteBackupInfo]]:
        try:
            remote_objects = self.remote_storage.objects()
        except Exception as e:
            raise MKGeneralException(
                f"Listing objects in remote storage failed. Original error: {e}"
            )
        for key in (el for el in remote_objects if BACKUP_INFO_FILENAME == el.name):
            try:
                yield str(key.parent), load_backup_info(self._get_file(key))
            except UnrecognizedBackupTypeError:
                continue

    def get_backup(self, backup_id: str) -> Backup:
        info = load_backup_info(self._get_file(Path(backup_id) / BACKUP_INFO_FILENAME))
        local_archive_file = self._get_file(Path(backup_id) / info.filename)
        verify_backup_file(info, local_archive_file)
        return Backup(info, backup_id, local_archive_file)

    def start_backup(self, job: Job) -> Path:
        return self.local_target.start_backup(job)

    def finish_backup(self, info: SiteBackupInfo, job: Job) -> Path:
        local_path_finished = self.local_target.finish_backup(info, job)
        remote_key_base = Path(local_path_finished.name)

        for local_path, remote_key in (
            (
                local_path_finished / info.filename,
                remote_key_base / info.filename,
            ),
            (
                local_path_finished / BACKUP_INFO_FILENAME,
                remote_key_base / BACKUP_INFO_FILENAME,
            ),
        ):
            try:
                log(f"Uploading {local_path} to remote storage ({remote_key})")
                self.remote_storage.upload(local_path, remote_key)
            except Exception as e:
                raise MKGeneralException(
                    f"Upload of {local_path} to {remote_key} failed. Original error: {e}"
                )

        return remote_key_base


class ProgressStepLogger:
    def __init__(self, *, logging_step_percentage: int = 10) -> None:
        self.logging_step_percentage: Final = logging_step_percentage
        self._next_logging_at = 0

    def __call__(self, progress_percentage: float) -> None:
        if progress_percentage >= self._next_logging_at:
            log(f"{progress_percentage:.1f} %")
            self._next_logging_at += self.logging_step_percentage
