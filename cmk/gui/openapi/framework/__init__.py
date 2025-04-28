#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Versioned REST API Framework

These types and functions are used to define the versioned REST API of Checkmk.
Once all endpoints are migrated to the new framework, the old marshmallow-based code can be removed.
"""

from ._types import HeaderParam, PathParam, QueryParam, RawRequestData

__all__ = [
    "HeaderParam",
    "PathParam",
    "QueryParam",
    "RawRequestData",
]
