/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HistogramParams } from '../histogram-params'

export { DEFAULT_QUANTILE } from '../histogram-params'

export type MetricType = 'gauge' | 'sum' | 'histogram'

export const METRIC_TYPES = ['gauge', 'sum', 'histogram'] as const

export type ConsolidationOutputType = 'float' | 'histogram'

export type GaugeFunction = 'gauge_last' | 'gauge_avg' | 'gauge_max' | 'gauge_min'

export type SumFunction = 'sum_rate' | 'sum_delta' | 'sum_last_raw'

export type HistogramFunction =
  | 'histogram_preserve'
  | 'histogram_count_rate'
  | 'histogram_count_delta'
  | 'histogram_sum_rate'
  | 'histogram_sum_delta'
  | 'histogram_quantile'
  | 'histogram_fraction_below'
  | 'histogram_fraction_between'
  | 'histogram_sum_raw'

type FunctionsByType = {
  gauge: GaugeFunction
  sum: SumFunction
  histogram: HistogramFunction
}

/** A function only exists within its metric type, so it travels as a type/function pair. */
export type ConsolidationFunction = {
  [T in MetricType]: { type: T; function: FunctionsByType[T] }
}[MetricType]

export type ConsolidationFunctionName = ConsolidationFunction['function']

export type ConsolidationParams = HistogramParams

export type ConsolidationModel = ConsolidationFunction & {
  params: ConsolidationParams
  lookbackSeconds: number
}

export interface FunctionSpec<F extends ConsolidationFunctionName = ConsolidationFunctionName> {
  fn: F
  /** Raw cumulative functions are marked "(raw)" and listed last. */
  raw: boolean
  output: ConsolidationOutputType
}

export const CONSOLIDATION_CATALOG: {
  [T in MetricType]: FunctionSpec<FunctionsByType[T]>[]
} = {
  gauge: [
    { fn: 'gauge_last', raw: false, output: 'float' },
    { fn: 'gauge_avg', raw: false, output: 'float' },
    { fn: 'gauge_max', raw: false, output: 'float' },
    { fn: 'gauge_min', raw: false, output: 'float' }
  ],
  sum: [
    { fn: 'sum_rate', raw: false, output: 'float' },
    { fn: 'sum_delta', raw: false, output: 'float' },
    { fn: 'sum_last_raw', raw: true, output: 'float' }
  ],
  histogram: [
    { fn: 'histogram_preserve', raw: false, output: 'histogram' },
    { fn: 'histogram_quantile', raw: false, output: 'float' },
    { fn: 'histogram_count_delta', raw: false, output: 'float' },
    { fn: 'histogram_count_rate', raw: false, output: 'float' },
    { fn: 'histogram_sum_delta', raw: false, output: 'float' },
    { fn: 'histogram_sum_rate', raw: false, output: 'float' },
    { fn: 'histogram_fraction_below', raw: false, output: 'float' },
    { fn: 'histogram_fraction_between', raw: false, output: 'float' },
    { fn: 'histogram_sum_raw', raw: true, output: 'float' }
  ]
}

export function functionSpec(
  type: MetricType,
  fn: ConsolidationFunctionName
): FunctionSpec | undefined {
  const specs: readonly FunctionSpec[] = CONSOLIDATION_CATALOG[type]
  return specs.find((spec) => spec.fn === fn)
}

/** The default function for a type is the first it offers (catalog order). */
export function defaultFunction(type: MetricType): ConsolidationFunction {
  switch (type) {
    case 'gauge':
      return { type, function: CONSOLIDATION_CATALOG[type][0]!.fn }
    case 'sum':
      return { type, function: CONSOLIDATION_CATALOG[type][0]!.fn }
    case 'histogram':
      return { type, function: CONSOLIDATION_CATALOG[type][0]!.fn }
  }
}

export function outputType(
  type: MetricType,
  fn: ConsolidationFunctionName
): ConsolidationOutputType {
  return functionSpec(type, fn)?.output ?? 'float'
}

/** The type/function pair of a model, without the editable params and lookback. */
export function consolidationFunctionOf(model: ConsolidationModel): ConsolidationFunction {
  const { params: _params, lookbackSeconds: _lookbackSeconds, ...fn } = model
  return fn
}

const PRESERVE_FUNCTION_SPELLINGS = [
  'histogram_preserve_quantile',
  'histogram_preserve_fraction_below',
  'histogram_preserve_fraction_between'
] as const

type PreserveFunctionSpelling = (typeof PRESERVE_FUNCTION_SPELLINGS)[number]

/**
 * A histogram_preserve_* spelling names a consolidation and a grouping at once; the
 * catalog holds only the "preserve histograms" half. Collapse a persisted or wire
 * spelling to that entry; every other name passes through.
 */
export function catalogFunctionName<N extends string>(
  name: N
): Exclude<N, PreserveFunctionSpelling> | 'histogram_preserve' {
  return (PRESERVE_FUNCTION_SPELLINGS as readonly string[]).includes(name)
    ? 'histogram_preserve'
    : (name as Exclude<N, PreserveFunctionSpelling>)
}

/** Resolve a persisted function name to its type/function pair; null for unknown names. */
export function consolidationFunctionFromName(name: string): ConsolidationFunction | null {
  for (const type of METRIC_TYPES) {
    for (const spec of CONSOLIDATION_CATALOG[type]) {
      if (spec.fn === name) {
        return { type, function: spec.fn } as ConsolidationFunction
      }
    }
  }
  return null
}
