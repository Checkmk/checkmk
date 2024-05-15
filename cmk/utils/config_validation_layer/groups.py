#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, Field

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD

GroupType = Literal["host", "service", "contact"]
GroupName = str
GroupSpec = dict[str, Any]
GroupSpecs = dict[GroupName, GroupSpec]
AllGroupSpecs = dict[GroupType, GroupSpecs]


# class GroupSpec(TypedDict):  # TODO: Use these types instead of the current dict[str, Any]
#     alias: str
#     customer: NotRequired[str]
#
#
# class ContactGroupSpec(GroupSpec):
#     inventory_paths: NotRequired[InventoryPaths]
#     nagvis_maps: NotRequired[Sequence[str | int]]

NothingOrChoices = Literal["nothing"] | tuple[Literal["choices"], list[str]]


class InventoryPath(TypedDict):
    visible_raw_path: str
    attributes: NotRequired[NothingOrChoices]
    columns: NotRequired[NothingOrChoices]
    nodes: NotRequired[NothingOrChoices]


InventoryPaths = Literal["allow_all"] | tuple[Literal["paths"], list[InventoryPath]]


class GroupAliasesModel(BaseModel):
    define_hostgroups: dict[GroupName, str] = Field(default_factory=dict)
    define_servicegroups: dict[GroupName, str] = Field(default_factory=dict)
    define_contactgroups: dict[GroupName, str] = Field(default_factory=dict)


class GroupConfigModel(BaseModel):
    customer: str | None | Omitted = OMITTED_FIELD


class ContactGroupConfigModel(GroupConfigModel):
    inventory_paths: InventoryPaths | Omitted = OMITTED_FIELD


class GroupConfigsModel(BaseModel):
    multisite_hostgroups: dict[GroupName, GroupConfigModel] = Field(default_factory=dict)
    multisite_servicegroups: dict[GroupName, GroupConfigModel] = Field(default_factory=dict)
    multisite_contactgroups: dict[GroupName, ContactGroupConfigModel] = Field(default_factory=dict)
