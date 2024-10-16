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
  topics: I18NTopics;
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
