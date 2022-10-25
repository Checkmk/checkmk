# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, NewType, Sequence, TypedDict

#########################################
# Schemas to share with CMA Backup tool #
# DO NOT CHANGE!                        #
#########################################

TargetId = NewType("TargetId", str)


class ScheduleConfig(TypedDict):
    disabled: bool
    period: str
    timeofday: Sequence[tuple[int, int]]


class JobConfig(TypedDict):
    title: str
    encrypt: str | None
    target: TargetId
    compress: bool
    schedule: ScheduleConfig | None
    no_history: bool
    without_sites: bool


class LocalTargetParams(TypedDict):
    path: str
    is_mountpoint: bool


LocalTargetConfig = tuple[Literal["local"], LocalTargetParams]


class TargetConfig(TypedDict):
    title: str
    remote: LocalTargetConfig


class Config(TypedDict):
    targets: dict[str, TargetConfig]
    jobs: dict[str, JobConfig]


class CMACluster(TypedDict):
    is_inactive: bool


class BackupInfo(TypedDict, total=False):
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
