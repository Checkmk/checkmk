#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Literal, NewType

# pydantic needs TypedDict from typing_extensions for < 3.11
from typing_extensions import NotRequired, TypedDict

#########################################
# Schemas to share with CMA Backup tool #
# DO NOT CHANGE!                        #
#########################################

TargetId = NewType("TargetId", str)


class ScheduleConfig(TypedDict):
    disabled: bool
    period: Literal["day"] | tuple[Literal["week"], int] | tuple[Literal["month_begin"], int]
    timeofday: Sequence[tuple[int, int]]


class JobConfig(TypedDict):
    title: str
    encrypt: str | None
    target: TargetId
    compress: bool
    schedule: ScheduleConfig | None
    no_history: bool
    # CMA jobs only, which we do not load, so we will never encounter this field. However, it's good
    # to know about it.
    without_sites: NotRequired[bool]


class LocalTargetParams(TypedDict):
    path: str
    is_mountpoint: bool


LocalTargetConfig = tuple[Literal["local"], LocalTargetParams]


class TargetConfig(TypedDict):
    title: str
    remote: LocalTargetConfig


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
class Job:
    config: JobConfig
    local_id: str
    id: str


@dataclass
class Backup:
    info: SiteBackupInfo
    id: str
    _path: Path

    @contextmanager
    def open(self) -> Iterator[IO[bytes]]:
        with self._path.open(mode="rb") as fh:
            yield fh
