#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

__all__ = [
    "ServiceName",
    "ContactgroupName",
    "CheckPluginNameStr",
    "Item",
    "MetricName",
]

ServiceName = str

ContactgroupName = str

CheckPluginNameStr = str
Item = str | None

MetricName = str
