#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

# NOTE: the underlying type for the `total_pages` parameter is int, but when you read the docs it
# says that it also supports all. So, an intermediate happy, we'll define our own type alias.
type TotalPages = int | Literal["all"]
"""The total pages argument that can be passed to Meraki SDK."""
