#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Protocol

from cmk.utils.backup.type_defs import Backup, SiteBackupInfo

from ..job import Job
from . import TargetId


class Target(Protocol):
    def __init__(self, target_id: TargetId, params: Mapping[str, object]) -> None: ...

    @property
    def id(self) -> TargetId: ...

    def check_ready(self) -> None: ...

    def list_backups(self) -> Iterator[tuple[str, SiteBackupInfo]]: ...

    def get_backup(self, backup_id: str) -> Backup: ...

    def start_backup(self, job: Job) -> Path: ...

    def finish_backup(self, info: SiteBackupInfo, job: Job) -> Path: ...
