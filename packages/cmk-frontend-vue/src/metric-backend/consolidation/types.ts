/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type MetricType = 'gauge' | 'sum' | 'histogram'

export const METRIC_TYPES = ['gauge', 'sum', 'histogram'] as const

export type ConsolidationOutputType = 'float' | 'histogram'

export type ConsolidationFunction =
  | 'last_value'
  | 'avg'
  | 'max'
  | 'min'
  | 'rate'
  | 'delta'
  | 'preserve_histogram'
  | 'count_rate'
  | 'count_delta'
  | 'sum_rate'
  | 'sum_delta'
  | 'quantile'
  | 'frac_below'
  | 'frac_between'

export interface ConsolidationParams {
  /** For 'quantile': the quantile in the range 0–1 (default 0.95). */
  quantile?: number
  /** For 'frac_below': the upper threshold. */
  fracBelow?: number
  /** For 'frac_between': the lower threshold. */
  fracLower?: number
  /** For 'frac_between': the upper threshold. */
  fracUpper?: number
}

export interface ConsolidationModel {
  /** Effective metric type the selected function belongs to. */
  type: MetricType
  function: ConsolidationFunction
  params: ConsolidationParams
  lookbackSeconds: number
}

export interface FunctionSpec {
  fn: ConsolidationFunction
  /** Raw cumulative functions are de-emphasised and listed after a divider. */
  raw: boolean
  output: ConsolidationOutputType
}

export const CONSOLIDATION_CATALOG: Record<MetricType, FunctionSpec[]> = {
  gauge: [
    { fn: 'last_value', raw: false, output: 'float' },
    { fn: 'avg', raw: false, output: 'float' },
    { fn: 'max', raw: false, output: 'float' },
    { fn: 'min', raw: false, output: 'float' }
  ],
  sum: [
    { fn: 'rate', raw: false, output: 'float' },
    { fn: 'delta', raw: false, output: 'float' },
    { fn: 'last_value', raw: true, output: 'float' }
  ],
  histogram: [
    { fn: 'preserve_histogram', raw: false, output: 'histogram' },
    { fn: 'count_delta', raw: false, output: 'float' },
    { fn: 'count_rate', raw: false, output: 'float' },
    { fn: 'sum_delta', raw: false, output: 'float' },
    { fn: 'sum_rate', raw: false, output: 'float' },
    { fn: 'quantile', raw: false, output: 'float' },
    { fn: 'frac_below', raw: false, output: 'float' },
    { fn: 'frac_between', raw: false, output: 'float' },
    { fn: 'last_value', raw: true, output: 'float' }
  ]
}

export function functionSpec(
  type: MetricType,
  fn: ConsolidationFunction
): FunctionSpec | undefined {
  return CONSOLIDATION_CATALOG[type].find((spec) => spec.fn === fn)
}

export function isFunctionValidForType(type: MetricType, fn: ConsolidationFunction): boolean {
  return functionSpec(type, fn) !== undefined
}

/** The default function for a type is the first (non-raw) entry of its catalog. */
export function defaultFunction(type: MetricType): ConsolidationFunction {
  return CONSOLIDATION_CATALOG[type][0]!.fn
}

export function outputType(type: MetricType, fn: ConsolidationFunction): ConsolidationOutputType {
  return functionSpec(type, fn)?.output ?? 'float'
}
