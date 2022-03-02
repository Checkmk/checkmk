#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
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

from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.bi.bi_lib import ReqBoolean, ReqConstant, ReqInteger, ReqNested, ReqString
from cmk.utils.bi.bi_schema import Schema


class BIAggregationVisualizationSchema(Schema):
    ignore_rule_styles = ReqBoolean(dump_default=False, example=False)
    layout_id = ReqString(dump_default="builtin_default", example="radial_layout2")
    line_style = ReqString(dump_default="round", example="round")


class BINodeVisNoneStyleSchema(Schema):
    type = ReqConstant("none")
    style_config = ReqConstant({})


# 'layout_style': {'style_config': {}}
class BINodeVisForceStyleSchema(Schema):
    type = ReqConstant("force")
    style_config = ReqConstant({})


# 'layout_style': {'style_config': {'degree': 80,
#                                   'radius': 25,
#                                   'rotation': 270},
class BINodeVisRadialStyleConfigSchema(Schema):
    degree = ReqInteger(dump_default=80)
    radius = ReqInteger(dump_default=25)
    rotation = ReqInteger(dump_default=270)


class BINodeVisRadialStyleSchema(Schema):
    type = ReqConstant("radial")
    style_config = ReqNested(BINodeVisRadialStyleConfigSchema)


#
# 'layout_style': {'style_config': {'layer_height': 80,
#                                   'node_size': 25,
#                                   'rotation': 270},
class BINodeVisHierarchyStyleConfigSchema(Schema):
    layer_height = ReqInteger(dump_default=80, example=85)
    node_size = ReqInteger(dump_default=25, example=40)
    rotation = ReqInteger(dump_default=270, example=180)


class BINodeVisHierarchyStyleSchema(Schema):
    type = ReqConstant("hierarchy")
    style_config = ReqNested(BINodeVisHierarchyStyleConfigSchema)


class BINodeVisBlockStyleSchema(Schema):
    type = ReqConstant("block")
    style_config = ReqConstant({})


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

    def get_obj_type(self, obj) -> str:
        return obj["type"]
