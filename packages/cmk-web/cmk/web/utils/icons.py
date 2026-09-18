#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The types naming an icon to render.

A static icon is picked from the set the frontend ships, so its name is checked
at type-check time. A dynamic icon is named at runtime - by a theme, a plug-in
or the user - and can therefore only be a string.

The generated names are re-exported here so that a caller needs a single import
for both halves.
"""

from dataclasses import dataclass
from typing import NewType, TypedDict

from cmk.shared_typing.icon import IconNames as IconNames
from cmk.shared_typing.icon import IconSizes as IconSizes

DynamicIconName = NewType("DynamicIconName", str)


class DynamicIconWithEmblem(TypedDict):
    icon: DynamicIconName
    emblem: str | None


DynamicIcon = DynamicIconName | DynamicIconWithEmblem


@dataclass(frozen=True)
class StaticIcon:
    icon: IconNames
    emblem: str | None = None


__all__ = [
    "DynamicIcon",
    "DynamicIconName",
    "DynamicIconWithEmblem",
    "IconNames",
    "IconSizes",
    "StaticIcon",
]
