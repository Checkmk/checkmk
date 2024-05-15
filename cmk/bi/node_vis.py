#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#   .--BIVis---------------------------------------------------------------.
#   |                       ____ _____     ___                             |
#   |                      | __ )_ _\ \   / (_)___                         |
#   |                      |  _ \| | \ \ / /| / __|                        |
#   |                      | |_) | |  \ V / | \__ \                        |
#   |                      |____/___|  \_/  |_|___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

from collections.abc import Mapping

from marshmallow_oneofschema import OneOfSchema

from cmk.bi.lib import ReqBoolean, ReqConstant, ReqInteger, ReqNested, ReqString
from cmk.bi.schema import Schema


class BIAggregationVisualizationSchema(Schema):
    ignore_rule_styles = ReqBoolean(
        dump_default=False, example=False, description="Ignore rule styles."
    )
    layout_id = ReqString(
        dump_default="builtin_default", example="radial_layout2", description="ID of the layout."
    )
    line_style = ReqString(dump_default="round", example="round", description="Line style to use.")


class BINodeVisNoneStyleSchema(Schema):
    type = ReqConstant("none", description="No specific child node visualization.")
    style_config = ReqConstant({}, description="No configuration options for this style.")


# 'layout_style': {'style_config': {}}
class BINodeVisForceStyleSchema(Schema):
    type = ReqConstant("force", description="Visualize child nodes based on force between them.")
    style_config = ReqConstant({}, description="No configuration options for this style.")


# 'layout_style': {'style_config': {'degree': 80,
#                                   'radius': 25,
#                                   'rotation': 270},
class BINodeVisRadialStyleConfigSchema(Schema):
    degree = ReqInteger(
        dump_default=80, description="Limits the child nodes to be within this angle."
    )
    radius = ReqInteger(dump_default=25, description="Distance between nodes.")
    rotation = ReqInteger(dump_default=270, description="Starting point of the angle, in degrees.")


class BINodeVisRadialStyleSchema(Schema):
    type = ReqConstant("radial", description="Visualize child nodes radially.")
    style_config = ReqNested(
        BINodeVisRadialStyleConfigSchema, description="Configuration options for this style."
    )


#
# 'layout_style': {'style_config': {'layer_height': 80,
#                                   'node_size': 25,
#                                   'rotation': 270},
class BINodeVisHierarchyStyleConfigSchema(Schema):
    layer_height = ReqInteger(dump_default=80, example=85, description="Distance between layers.")
    node_size = ReqInteger(
        dump_default=25, example=40, description="Distance between nodes within the same layer."
    )
    rotation = ReqInteger(
        dump_default=270, example=180, description="Rotation of the hierarchy, in degrees."
    )


class BINodeVisHierarchyStyleSchema(Schema):
    type = ReqConstant("hierarchy", description="Visualize child nodes in a hierarchy.")
    style_config = ReqNested(
        BINodeVisHierarchyStyleConfigSchema, description="Configuration options for this style."
    )


class BINodeVisBlockStyleSchema(Schema):
    type = ReqConstant("block", description="Visualize child nodes as a block.")
    style_config = ReqConstant({}, description="No configuration options for this style.")


class BINodeVisLayoutStyleSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False

    type_schemas = {
        "none": BINodeVisNoneStyleSchema,
        "block": BINodeVisBlockStyleSchema,
        "hierarchy": BINodeVisHierarchyStyleSchema,
        "radial": BINodeVisRadialStyleSchema,
        "force": BINodeVisForceStyleSchema,
    }

    def get_obj_type(self, obj: Mapping[str, str]) -> str:
        return obj["type"]
