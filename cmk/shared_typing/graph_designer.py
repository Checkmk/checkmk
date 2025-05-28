#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# This file is auto-generated via the cmk-shared-typing package.
# Do not edit manually.
#
# fmt: off


from __future__ import annotations

from typing import Literal, Sequence

from pydantic import BaseModel


class Metric(BaseModel):
    id: int
    type: Literal["metric"] = "metric"
    color: str
    auto_title: str
    custom_title: str
    visible: bool
    line_type: Literal["line", "area", "stack"]
    mirrored: bool
    host_name: str
    service_name: str
    metric_name: str
    consolidation_type: Literal["average", "min", "max"]


class Scalar(BaseModel):
    id: int
    type: Literal["scalar"] = "scalar"
    color: str
    auto_title: str
    custom_title: str
    visible: bool
    line_type: Literal["line", "area", "stack"]
    mirrored: bool
    host_name: str
    service_name: str
    metric_name: str
    scalar_type: Literal["warn", "crit", "min", "max"]


class Constant(BaseModel):
    id: int
    type: Literal["constant"] = "constant"
    color: str
    auto_title: str
    custom_title: str
    visible: bool
    line_type: Literal["line", "area", "stack"]
    mirrored: bool
    value: float


class GraphOptionUnitCustomNotationWithSymbol(BaseModel):
    type: Literal[
        "decimal", "si", "iec", "standard_scientific", "engineering_scientific"
    ]
    symbol: str


class GraphOptionUnitCustomPrecision(BaseModel):
    type: Literal["auto", "strict"]
    digits: int


class GraphOptionUnitCustom(BaseModel):
    notation: GraphOptionUnitCustomNotationWithSymbol | Literal["time"]
    precision: GraphOptionUnitCustomPrecision


class GraphOptionExplicitVerticalRangeBoundaries(BaseModel):
    lower: float
    upper: float


class GraphOptions(BaseModel):
    unit: Literal["first_entry_with_unit"] | GraphOptionUnitCustom
    explicit_vertical_range: (
        Literal["auto"] | GraphOptionExplicitVerticalRangeBoundaries
    )
    omit_zero_metrics: bool


class I18nGraphLines(BaseModel):
    of: str
    average: str
    warning: str
    critical: str
    minimum: str
    maximum: str
    actions: str
    color: str
    auto_title: str
    custom_title: str
    visible: str
    line_style: str
    line: str
    area: str
    stack: str
    mirrored: str
    formula: str
    dissolve_operation: str
    clone_this_entry: str
    move_this_entry: str
    delete_this_entry: str
    add: str


class I18nGraphOperations(BaseModel):
    sum: str
    product: str
    difference: str
    fraction: str
    average: str
    minimum: str
    maximum: str
    no_selected_graph_lines: str
    percentile: str
    apply: str
    no_selected_graph_line: str


class I18nGraphOptions(BaseModel):
    unit_first_entry_with_unit: str
    unit_custom: str
    unit_custom_notation: str
    unit_custom_notation_symbol: str
    unit_custom_notation_decimal: str
    unit_custom_notation_si: str
    unit_custom_notation_iec: str
    unit_custom_notation_standard_scientific: str
    unit_custom_notation_engineering_scientific: str
    unit_custom_notation_time: str
    unit_custom_precision: str
    unit_custom_precision_type: str
    unit_custom_precision_type_auto: str
    unit_custom_precision_type_strict: str
    unit_custom_precision_digits: str
    explicit_vertical_range_auto: str
    explicit_vertical_range_explicit: str
    explicit_vertical_range_explicit_lower: str
    explicit_vertical_range_explicit_upper: str


class I18nTopics(BaseModel):
    metric: str
    scalar: str
    constant: str
    graph_lines: str
    operations: str
    transformation: str
    graph_operations: str
    unit: str
    explicit_vertical_range: str
    omit_zero_metrics: str
    graph_options: str


class I18n(BaseModel):
    graph_lines: I18nGraphLines
    graph_operations: I18nGraphOperations
    graph_options: I18nGraphOptions
    topics: I18nTopics


class GraphDesignerContent(BaseModel):
    graph_lines: Sequence[Metric | Scalar | Constant | Operation | Transformation]
    graph_options: GraphOptions
    i18n: I18n


class Operation(BaseModel):
    id: int
    type: Literal[
        "sum", "product", "difference", "fraction", "average", "minimum", "maximum"
    ]
    color: str
    auto_title: str
    custom_title: str
    visible: bool
    line_type: Literal["line", "area", "stack"]
    mirrored: bool
    operands: Sequence[Metric | Scalar | Constant | Operation | Transformation]


class Transformation(BaseModel):
    id: int
    type: Literal["transformation"] = "transformation"
    color: str
    auto_title: str
    custom_title: str
    visible: bool
    line_type: Literal["line", "area", "stack"]
    mirrored: bool
    percentile: float
    operand: Metric | Scalar | Constant | Operation | Transformation


GraphDesignerContent.update_forward_refs()
Operation.update_forward_refs()
Transformation.update_forward_refs()
