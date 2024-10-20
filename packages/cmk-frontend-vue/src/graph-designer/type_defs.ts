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

export type GraphLines = [] | [GraphLine];
export type GraphLineId = number;
export type GraphLineColor = string;
export type GraphLineTitle = string;
export type GraphLineTitleShort = string;
export type GraphLineVisible = boolean;
export type GraphLineLineType = "line" | "area" | "stack'";
export type GraphLineMirrored = boolean;

export interface GraphDesignerContent {
  graph_lines: GraphLines;
  i18n: I18N;
}
export interface GraphLine {
  id: GraphLineId;
  color: GraphLineColor;
  title: GraphLineTitle;
  title_short: GraphLineTitleShort;
  visible: GraphLineVisible;
  line_type: GraphLineLineType;
  mirrored: GraphLineMirrored;
}
export interface I18N {
  graph_lines: I18NGraphLines;
  graph_operations: I18NGraphOperations;
  graph_options: I18NGraphOptions;
  topics: I18NTopics;
}
export interface I18NGraphLines {
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
  unit_first_with_unit: string;
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
  unit_custom_precision_rounding_mode: string;
  unit_custom_precision_rounding_mode_auto: string;
  unit_custom_precision_rounding_mode_strict: string;
  unit_custom_precision_digits: string;
  vertical_range_auto: string;
  vertical_range_explicit: string;
  vertical_range_explicit_lower: string;
  vertical_range_explicit_upper: string;
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
  vertical_range: string;
  metrics_with_zero_values: string;
  graph_options: string;
}
