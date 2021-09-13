#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module contains type definitions that users can use if they choose
to leverage the power of type annotations in their check plugins.

Example:

    For a parse function that creates a dictionary for every item, for instance,
    you could use

    >>> from typing import Any, Mapping
    >>>
    >>> def parse_my_plugin(string_table: StringTable) -> Mapping[str, Mapping[str, str]]:
    ...     pass
    >>>
    >>> # A check function handling such data should be annotated
    >>> def check_my_plugin(
    ...     item: str,
    ...     params: Mapping[str, Any],
    ...     section: Mapping[str, Mapping[str, str]],
    ... ) -> CheckResult:
    ...     pass

"""

from cmk.base.api.agent_based.checking_classes import CheckResult, DiscoveryResult
from cmk.base.api.agent_based.inventory_classes import InventoryResult
from cmk.base.api.agent_based.type_defs import HostLabelGenerator, StringByteTable, StringTable

__all__ = [
    "CheckResult",
    "DiscoveryResult",
    "HostLabelGenerator",
    "InventoryResult",
    "StringByteTable",
    "StringTable",
]
