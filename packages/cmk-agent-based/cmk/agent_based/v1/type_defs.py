#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module contains type definitions that users can use if they choose
to leverage the power of type annotations in their check plug-ins.

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

from collections.abc import Generator as _Generator
from collections.abc import Iterable as _Iterable
from typing import List as _List

from ._checking_classes import CheckResult, DiscoveryResult
from ._checking_classes import HostLabel as _HostLabel
from ._inventory_classes import Attributes as _Attributes
from ._inventory_classes import TableRow as _TableRow

InventoryResult = _Iterable[_Attributes | _TableRow]

# unfortunately we really need 'List' here, not 'list'.
StringTable = _List[_List[str]]
StringByteTable = _List[_List[str | _List[int]]]

HostLabelGenerator = _Generator[_HostLabel, None, None]


__all__ = [
    "CheckResult",
    "DiscoveryResult",
    "HostLabelGenerator",
    "InventoryResult",
    "StringByteTable",
    "StringTable",
]
