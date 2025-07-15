#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal, TypedDict

from marshmallow_oneofschema import OneOfSchema

from cmk import fields
from cmk.gui.fields.base import BaseSchema


class NoRestriction(BaseSchema):
    type = fields.Constant(
        "no_restriction",
        description="No restriction on the path.",
    )


class RestrictAll(BaseSchema):
    type = fields.Constant(
        "restrict_all",
        description="Restrict all values.",
    )


class RestrictValues(BaseSchema):
    type = fields.Constant(
        "restrict_values",
        description="Restrict specific values.",
    )
    values = fields.List(
        fields.String(),
        required=True,
        description="A list of values to be allowed.",
        minLength=1,
    )


class PathRestriction(OneOfSchema):
    type_field_remove = False
    type_field = "type"
    type_schemas = {
        "no_restriction": NoRestriction,
        "restrict_all": RestrictAll,
        "restrict_values": RestrictValues,
    }

    def get_obj_type(self, obj: object) -> str:
        if isinstance(obj, dict):
            if self.type_field in obj:
                return obj[self.type_field]

        return super().get_obj_type(obj)


class InventoryPathSpecificPath(BaseSchema):
    path = fields.String(
        required=True,
        description="Path to category.",
    )
    attributes = fields.Nested(
        PathRestriction,
        load_default=lambda: {"type": "no_restriction"},
        description="Restrict single values.",
    )
    columns = fields.Nested(
        PathRestriction,
        load_default=lambda: {"type": "no_restriction"},
        description="Restrict table columns.",
    )
    nodes = fields.Nested(
        PathRestriction,
        load_default=lambda: {"type": "no_restriction"},
        description="Restrict subcategories.",
    )


class InventoryPathSpecificPaths(BaseSchema):
    type = fields.Constant(
        "specific_paths",
        description="Allowed to see parts of the tree.",
    )
    paths = fields.List(
        fields.Nested(InventoryPathSpecificPath),
        required=True,
        description="A list of paths to be allowed.",
    )


class InventoryPathAllowAll(BaseSchema):
    type = fields.Constant(
        "allow_all",
        description="Allowed to see the whole tree.",
    )


class InventoryPathForbidAll(BaseSchema):
    type = fields.Constant(
        "forbid_all",
        description="Forbidden to see the whole tree.",
    )


class InventoryPaths(OneOfSchema):
    type_field_remove = False
    type_field = "type"
    type_schemas = {
        "allow_all": InventoryPathAllowAll,
        "forbid_all": InventoryPathForbidAll,
        "specific_paths": InventoryPathSpecificPaths,
    }

    def get_obj_type(self, obj: object) -> str:
        if isinstance(obj, dict):
            if self.type_field in obj:
                return obj[self.type_field]

        return super().get_obj_type(obj)


class APINoRestriction(TypedDict):
    type: Literal["no_restriction"]


class APIRestrictAll(TypedDict):
    type: Literal["restrict_all"]


class APIRestrictValues(TypedDict):
    type: Literal["restrict_values"]
    values: list[str]


APIPathRestriction = APINoRestriction | APIRestrictAll | APIRestrictValues


class APIPermittedPath(TypedDict):
    path: str
    attributes: APIPathRestriction
    columns: APIPathRestriction
    nodes: APIPathRestriction


class APIInventoryPathSpecificPaths(TypedDict):
    type: Literal["specific_paths"]
    paths: list[APIPermittedPath]


class APIInventoryPathAllowAll(TypedDict):
    type: Literal["allow_all"]


class APIInventoryPathForbidAll(TypedDict):
    type: Literal["forbid_all"]


APIInventoryPaths = (
    APIInventoryPathAllowAll | APIInventoryPathForbidAll | APIInventoryPathSpecificPaths
)

APIGroupSpec = dict[str, Any]
