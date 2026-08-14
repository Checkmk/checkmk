/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AttributeKind } from '../attribute-kind'
import type { ConsolidationOutputType } from '../consolidation/types'
import type { HistogramParams } from '../histogram-params'

export type { AttributeKind }

export type GroupByInputType = ConsolidationOutputType

// Catalog order is the dropdown order; the first entry of each list is the default.
export const FLOAT_FUNCTIONS = ['none', 'avg', 'min', 'max', 'sum', 'count'] as const
export const HISTOGRAM_FUNCTIONS = ['percentile', 'fraction_below', 'fraction_between'] as const

export type FloatFunction = (typeof FLOAT_FUNCTIONS)[number]
export type HistogramFunction = (typeof HISTOGRAM_FUNCTIONS)[number]
export type GroupByFunction = FloatFunction | HistogramFunction

export type ParamKind = 'quantile' | 'fraction_below' | 'fraction_between' | 'none'

export interface GroupKey {
  id: string
  attributeKind: AttributeKind | null
  attributeKey: string
}

export interface GroupByModel {
  function: GroupByFunction
  params: HistogramParams
  keys: GroupKey[]
}

/** The grouping functions offered for an input type, in catalog (dropdown) order. */
export function functionsForInputType(type: GroupByInputType): readonly GroupByFunction[] {
  return type === 'histogram' ? HISTOGRAM_FUNCTIONS : FLOAT_FUNCTIONS
}

export function isFunctionValidForInputType(type: GroupByInputType, fn: GroupByFunction): boolean {
  return functionsForInputType(type).includes(fn)
}

export function defaultFunction(type: GroupByInputType): GroupByFunction {
  return functionsForInputType(type)[0]!
}

/** Coerce a grouping to an input type, resetting an incompatible function while keeping its keys. */
export function groupByForInputType(type: GroupByInputType, groupBy: GroupByModel): GroupByModel {
  return isFunctionValidForInputType(type, groupBy.function)
    ? groupBy
    : { function: defaultFunction(type), params: {}, keys: groupBy.keys }
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

export type ValidGroupKey = GroupKey & { attributeKind: AttributeKind }

export function isKeyValid(key: GroupKey): key is ValidGroupKey {
  return key.attributeKey !== '' && key.attributeKind !== null
}
