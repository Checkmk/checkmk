#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from ._localize import Label, Title
from ._node import (
    BoolField,
    ChoiceField,
    Node,
    NumberField,
    Table,
    TextField,
    View,
)
from ._style import Alignment, BackgroundColor, LabelColor
from ._unit import (
    AgeNotation,
    AutoPrecision,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)


def entry_point_prefixes() -> Mapping[type[Node], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    node_... = Node(...)
    """
    return {
        Node: "node_",
    }


__all__ = [
    "AgeNotation",
    "Alignment",
    "AutoPrecision",
    "BackgroundColor",
    "BoolField",
    "ChoiceField",
    "DecimalNotation",
    "EngineeringScientificNotation",
    "IECNotation",
    "Label",
    "LabelColor",
    "Node",
    "NumberField",
    "SINotation",
    "StandardScientificNotation",
    "StrictPrecision",
    "Table",
    "TextField",
    "TimeNotation",
    "Title",
    "Unit",
    "View",
    "entry_point_prefixes",
]
