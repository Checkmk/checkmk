#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Parsing helpers for Azure resource IDs.

This module must stay stdlib-only (see package docstring).
"""

from collections.abc import Sequence


def get_params_from_azure_id(
    resource_id: str, resource_types: Sequence[str] | None = None
) -> Sequence[str]:
    values = resource_id.lower().split("/")
    type_strings = list(map(str.lower, resource_types)) if resource_types else []
    index_keywords = ["subscriptions", "resourcegroups"] + type_strings
    return [values[values.index(keyword) + 1] for keyword in index_keywords]
