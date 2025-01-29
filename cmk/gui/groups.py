#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Literal

GroupName = str
GroupSpec = dict[str, Any]
GroupSpecs = dict[GroupName, GroupSpec]
GroupType = Literal["host", "service", "contact"]
AllGroupSpecs = dict[GroupType, GroupSpecs]

# class GroupSpec(TypedDict):  # TODO: Use these types instead of the current dict[str, Any]
#     alias: str
#     customer: NotRequired[str]
#
#
# class ContactGroupSpec(GroupSpec):
#     inventory_paths: NotRequired[InventoryPaths]
#     nagvis_maps: NotRequired[Sequence[str | int]]
