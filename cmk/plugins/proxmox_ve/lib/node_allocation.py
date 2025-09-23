#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic import BaseModel


class SectionNodeAllocation(BaseModel, frozen=True):
    allocated_cpu: float
    node_total_cpu: float
    allocated_mem: float
    node_total_mem: float
    status: str
