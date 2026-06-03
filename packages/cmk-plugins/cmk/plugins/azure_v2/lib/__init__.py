#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared Azure helpers, importable outside the plugin context.

The modules in this package should stay stdlib-only - it also intended
for the consume _outside_ the azure package.
"""

from cmk.plugins.azure_v2.lib.constants import (
    get_resource_type_abbreviation,
    RESOURCE_TYPE_ABBREVIATIONS,
)
from cmk.plugins.azure_v2.lib.hostname import compute_unique_name_hash
from cmk.plugins.azure_v2.lib.resource_id import get_params_from_azure_id

__all__ = [
    "compute_unique_name_hash",
    "get_params_from_azure_id",
    "get_resource_type_abbreviation",
    "RESOURCE_TYPE_ABBREVIATIONS",
]
