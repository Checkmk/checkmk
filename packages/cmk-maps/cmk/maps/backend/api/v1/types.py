#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared Pydantic/FastAPI type aliases for v1 endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Path

# Map names end up as filenames (under maps_dir) and as path components
# in Checkmk permission lookups. Restricting the character set here prevents
# path traversal and odd permission-key lookups before the value reaches any
# business logic.
MapName = Annotated[
    str,
    Path(pattern=r"^[a-zA-Z0-9_\-]+$", min_length=1, max_length=100),
]
