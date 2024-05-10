#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################
# Schemas to share with CMA Backup tool #
# DO NOT CHANGE!                        #
#########################################


from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TypedDict

from .job import JobConfig


class CMACluster(TypedDict):
    is_inactive: bool


class RawBackupInfo(TypedDict, total=False):
    config: JobConfig
    files: Sequence[tuple[str, int, str]]
    finished: float
    hostname: str
    job_id: str
    site_id: str
    site_version: str
    size: int
    type: str
    backup_id: str
    cma_cluster: CMACluster
    cma_version: str


@dataclass(frozen=True)
class SiteBackupInfo:
    config: JobConfig
    filename: str
    checksum: str
    finished: float
    hostname: str
    job_id: str
    site_id: str
    site_version: str
    size: int


@dataclass
class Backup:
    info: SiteBackupInfo
    id: str
    _path: Path

    @contextmanager
    def open(self) -> Iterator[IO[bytes]]:
        with self._path.open(mode="rb") as fh:
            yield fh
