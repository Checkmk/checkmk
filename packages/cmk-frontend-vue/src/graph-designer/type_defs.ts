/**
 * Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable */
/**
 * This file is auto-generated via the cmk-shared-typing package.
 * Do not edit manually.
 */

export type GraphLine = Metric | Scalar | Constant | Operation | Transformation;
export type GraphLineId = number;
export type GraphLineColor = string;
export type GraphLineTitle = string;
export type GraphLineVisible = boolean;
export type GraphLineLineType = "line" | "area" | "stack";
export type GraphLineMirrored = boolean;
export type GraphLineHostName = string;
export type GraphLineServiceName = string;
export type GraphLineMetricName = string;
export type GraphLines = GraphLine[];
export type GraphOptionUnitCustomNotation = GraphOptionUnitCustomNotationWithSymbol | "time";

export interface GraphDesignerContent {
  graph_lines: GraphLines;
  graph_options: GraphOptions;
  i18n: I18N;
}
export interface Metric {
  id: GraphLineId;
  type: "metric";
  color: GraphLineColor;
  title: GraphLineTitle;
  visible: GraphLineVisible;
  line_type: GraphLineLineType;
  mirrored: GraphLineMirrored;
  host_name: GraphLineHostName;
  service_name: GraphLineServiceName;
  metric_name: GraphLineMetricName;
  consolidation_type: "average" | "min" | "max";
}
export interface Scalar {
  id: GraphLineId;
  type: "scalar";
  color: GraphLineColor;
  title: GraphLineTitle;
  visible: GraphLineVisible;
  line_type: GraphLineLineType;
  mirrored: GraphLineMirrored;
  host_name: GraphLineHostName;
  service_name: GraphLineServiceName;
  metric_name: GraphLineMetricName;
  scalar_type: "warn" | "crit" | "min" | "max";
}
export interface Constant {
  id: GraphLineId;
  type: "constant";
  color: GraphLineColor;
  title: GraphLineTitle;
  visible: GraphLineVisible;
  line_type: GraphLineLineType;
  mirrored: GraphLineMirrored;
  value: number;
}
export interface Operation {
  id: GraphLineId;
  type: "sum" | "product" | "difference" | "fraction" | "average" | "minimum" | "maximum";
  color: GraphLineColor;
  title: GraphLineTitle;
  visible: GraphLineVisible;
  line_type: GraphLineLineType;
  mirrored: GraphLineMirrored;
  operands: (Metric | Scalar | Constant | Operation | Transformation)[];
}
export interface Transformation {
  id: GraphLineId;
  type: "transformation";
  color: GraphLineColor;
  title: GraphLineTitle;
  visible: GraphLineVisible;
  line_type: GraphLineLineType;
  mirrored: GraphLineMirrored;
  percentile: number;
  operand: GraphLine;
}
export interface GraphOptions {
  unit: "first_entry_with_unit" | GraphOptionUnitCustom;
  explicit_vertical_range: "auto" | GraphOptionExplicitVerticalRangeBoundaries;
  omit_zero_metrics: boolean;
}
export interface GraphOptionUnitCustom {
  notation: GraphOptionUnitCustomNotation;
  precision: GraphOptionUnitCustomPrecision;
}
export interface GraphOptionUnitCustomNotationWithSymbol {
  type: "decimal" | "si" | "iec" | "standard_scientific" | "engineering_scientific";
  symbol: string;
}
export interface GraphOptionUnitCustomPrecision {
  type: "auto" | "strict";
  digits: number;
}
export interface GraphOptionExplicitVerticalRangeBoundaries {
  lower: number;
  upper: number;
}
export interface I18N {
  graph_lines: I18NGraphLines;
  graph_operations: I18NGraphOperations;
  graph_options: I18NGraphOptions;
  topics: I18NTopics;
}
export interface I18NGraphLines {
  of: string;
  average: string;
  warning: string;
  critical: string;
  minimum: string;
  maximum: string;
  actions: string;
  color: string;
  title: string;
  visible: string;
  line_style: string;
  line: string;
  area: string;
  stack: string;
  mirrored: string;
  formula: string;
  dissolve_operation: string;
  clone_this_entry: string;
  move_this_entry: string;
  delete_this_entry: string;
  add: string;
}
export interface I18NGraphOperations {
  sum: string;
  product: string;
  difference: string;
  fraction: string;
  average: string;
  minimum: string;
  maximum: string;
  no_selected_graph_lines: string;
  percentile: string;
  apply: string;
  no_selected_graph_line: string;
}
export interface I18NGraphOptions {
  unit_first_entry_with_unit: string;
  unit_custom: string;
  unit_custom_notation: string;
  unit_custom_notation_symbol: string;
  unit_custom_notation_decimal: string;
  unit_custom_notation_si: string;
  unit_custom_notation_iec: string;
  unit_custom_notation_standard_scientific: string;
  unit_custom_notation_engineering_scientific: string;
  unit_custom_notation_time: string;
  unit_custom_precision: string;
  unit_custom_precision_type: string;
  unit_custom_precision_type_auto: string;
  unit_custom_precision_type_strict: string;
  unit_custom_precision_digits: string;
  explicit_vertical_range_auto: string;
  explicit_vertical_range_explicit: string;
  explicit_vertical_range_explicit_lower: string;
  explicit_vertical_range_explicit_upper: string;
}
export interface I18NTopics {
  metric: string;
  scalar: string;
  constant: string;
  graph_lines: string;
  operations: string;
  transformation: string;
  graph_operations: string;
  unit: string;
  explicit_vertical_range: string;
  omit_zero_metrics: string;
  graph_options: string;
}
