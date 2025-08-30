#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ._registration import register_endpoints
from .model.widget_content.graph import ApiCustomGraphValidation

__all__ = [
    "ApiCustomGraphValidation",
    "register_endpoints",
]
