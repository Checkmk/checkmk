#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class LockState(Enum):
    BACKUP = "backup"
    CLONE = "clone"
    CREATE = "create"
    DESTROYED = "destroyed"
    DISK = "disk"
    FSTRIM = "fstrim"
    IMPORT = "import"
    MIGRATE = "migrate"
    MOUNTED = "mounted"
    ROLLBACK = "rollback"
    SNAPSHOT = "snapshot"
    SNAPSHOT_DELETE = "snapshot-delete"
    SUSPENDING = "suspending"
    SUSPENDED = "suspended"

    @classmethod
    def parse(cls, raw: str) -> LockState | str:
        try:
            return cls(raw)
        except ValueError:
            return raw


class SectionVMInfo(BaseModel, frozen=True):
    vmid: str
    node: str
    status: str
    type: Literal["qemu", "lxc"]
    name: str
    tags: tuple[str, ...] = ()
    uptime: int = Field(default=0, ge=0)
    lock: LockState | str | None = Field(default=None, union_mode="left_to_right")
    cluster: str | None = None
