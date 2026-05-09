#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################
# Schemas to share with CMA Backup tool #
# DO NOT CHANGE!                        #
#########################################

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

from pydantic import BaseModel

from .targets import TargetId


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


@dataclass
class Job:
    config: JobConfig
    local_id: str
    id: str


class JobState(BaseModel):
    state: str | None
    started: float | None
    output: str
    bytes_per_second: float | None = None
    finished: float | None = None
    next_schedule: str | float | None = None
    pid: int | None = None
    size: int | None = None
    success: bool = False
