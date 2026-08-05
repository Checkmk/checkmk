/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConsolidationOutputType } from '../consolidation/types'
import type { HistogramParams } from '../histogram-params'

export type GroupByInputType = ConsolidationOutputType

// Catalog order is the dropdown order; the first entry of each list is the default.
export const FLOAT_FUNCTIONS = ['none', 'avg', 'min', 'max', 'sum', 'count'] as const
export const HISTOGRAM_FUNCTIONS = ['percentile', 'fraction_below', 'fraction_between'] as const

export const GROUP_LEVELS = ['resource', 'scope', 'data_point'] as const

export type FloatFunction = (typeof FLOAT_FUNCTIONS)[number]
export type HistogramFunction = (typeof HISTOGRAM_FUNCTIONS)[number]
export type GroupByFunction = FloatFunction | HistogramFunction
export type GroupLevel = (typeof GROUP_LEVELS)[number]

export type ParamKind = 'quantile' | 'fraction_below' | 'fraction_between' | 'none'

export interface GroupKey {
  id: string
  level: GroupLevel
  key: string
}

export interface GroupByModel {
  function: GroupByFunction
  params: HistogramParams
  keys: GroupKey[]
}

/**
 * The grouping functions offered for an input type, in catalog (dropdown) order.
 *
 * `allowed` narrows that catalog: a histogram_preserve line passes ['percentile'], so
 * histogram + percentile stays and histogram + fraction_below drops out. Omitted, every
 * function of the type is offered.
 */
export function functionsForInputType(
  type: GroupByInputType,
  allowed?: readonly GroupByFunction[]
): readonly GroupByFunction[] {
  const all = type === 'histogram' ? HISTOGRAM_FUNCTIONS : FLOAT_FUNCTIONS
  if (allowed === undefined) {
    return all
  }
  return all.filter((fn) => allowed.includes(fn))
}

export function isFunctionValidForInputType(
  type: GroupByInputType,
  fn: GroupByFunction,
  allowed?: readonly GroupByFunction[]
): boolean {
  return functionsForInputType(type, allowed).includes(fn)
}

export function defaultFunction(
  type: GroupByInputType,
  allowed?: readonly GroupByFunction[]
): GroupByFunction {
  return functionsForInputType(type, allowed)[0]!
}

export function functionTakesKeys(fn: GroupByFunction): boolean {
  return fn !== 'none'
}

export function functionParamKind(fn: GroupByFunction): ParamKind {
  switch (fn) {
    case 'percentile':
      return 'quantile'
    case 'fraction_below':
      return 'fraction_below'
    case 'fraction_between':
      return 'fraction_between'
    default:
      return 'none'
  }
}

export function isKeyValid(key: GroupKey): boolean {
  return key.key !== ''
}
