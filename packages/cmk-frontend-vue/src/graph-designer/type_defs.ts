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

export interface GraphDesignerContent {
  i18n: I18N;
}
export interface I18N {
  graph_options: I18NGraphOptions;
  topics: I18NTopics;
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
