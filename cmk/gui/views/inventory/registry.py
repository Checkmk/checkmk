#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from typing import override, TypedDict

from cmk.ccc.plugin_registry import Registry
from cmk.gui.inventory.filters import (
    FilterInvBool,
    FilterInvFloat,
    FilterInvtableAdminStatus,
    FilterInvtableAvailable,
    FilterInvtableIntegerRange,
    FilterInvtableInterfaceType,
    FilterInvtableOperStatus,
    FilterInvtableText,
    FilterInvtableTimestampAsAge,
    FilterInvtableVersion,
    FilterInvText,
)
from cmk.inventory.structured_data import SDValue
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import DynamicIconName
from cmk.web.utils.speaklater import LazyString

SortFunction = Callable[[SDValue, SDValue], int]


class InventoryHintSpec(TypedDict, total=False):
    title: str | LazyString | Callable[[str], str]
    short: str | LazyString
    icon: DynamicIconName
    paint: str
    view: str
    keyorder: Sequence[str]
    sort: SortFunction
    filter: (
        type[FilterInvText]
        | type[FilterInvBool]
        | type[FilterInvFloat]
        | type[FilterInvtableAdminStatus]
        | type[FilterInvtableAvailable]
        | type[FilterInvtableIntegerRange]
        | type[FilterInvtableInterfaceType]
        | type[FilterInvtableOperStatus]
        | type[FilterInvtableText]
        | type[FilterInvtableTimestampAsAge]
        | type[FilterInvtableVersion]
    )
    is_show_more: bool


InventoryHintRegistry = dict[str, InventoryHintSpec]
inventory_displayhints: InventoryHintRegistry = {}


PaintResult = tuple[str, str | HTML]
PaintFunction = Callable[[SDValue], PaintResult]


class InvPaintFunction(TypedDict):
    name: str
    func: PaintFunction


class InvPaintFunctions(Registry[InvPaintFunction]):
    @override
    def plugin_name(self, instance: InvPaintFunction) -> str:
        return instance["name"]


inv_paint_funtions = InvPaintFunctions()
