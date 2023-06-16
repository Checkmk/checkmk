#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict

__all__ = [
    "HostOrServiceConditionRegex",
    "HostOrServiceConditionsSimple",
    "HostOrServiceConditionsNegated",
    "HostOrServiceConditions",
]

# TODO: These types call for a better name and a higher, common
#       abstraction such as an ABC.

HostOrServiceConditionRegex = TypedDict(
    "HostOrServiceConditionRegex",
    {"$regex": str},
)
HostOrServiceConditionsSimple = list[HostOrServiceConditionRegex | str]
HostOrServiceConditionsNegated = TypedDict(
    "HostOrServiceConditionsNegated",
    {"$nor": HostOrServiceConditionsSimple},
)

HostOrServiceConditions = HostOrServiceConditionsSimple | HostOrServiceConditionsNegated
