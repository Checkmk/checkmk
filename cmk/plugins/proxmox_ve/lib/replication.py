#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from pydantic import BaseModel, Field


class Replication(BaseModel, frozen=True):
    id: str
    source: str
    target: str
    schedule: str
    last_sync: int
    last_try: int
    next_sync: int
    duration: float
    error: str | None = Field(default=None)


class SectionReplication(BaseModel, frozen=True):
    node: str
    replications: Sequence[Replication]
    cluster_has_replications: bool
