#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from pydantic import BaseModel, Field


class SectionVMInfo(BaseModel, frozen=True):
    vmid: str
    node: str
    status: str
    type: Literal["qemu", "lxc"]
    name: str
    uptime: int = Field(default=0, ge=0)
    lock: str | None = None
