/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import type { ApiFormulaNodeInput } from './calculation/formula/convert'
import type { Formula } from './calculation/formula/grammar'
import type { DesignerConsolidationFunction } from './consolidation'

/** Default `title` for every new item. */
export const DEFAULT_TITLE_MACRO = '$DEFAULT_TITLE$'

/** Spreadsheet-style identifier: 'A'..'Z','AA','AB',... — unique across all items. */
export type ItemId = string

// Item shapes are the REST API data-source schemas.
export type RRDMetricItem = components['schemas']['CustomGraphRRDMetricDataSource']
export type RRDQueryItem = components['schemas']['CustomGraphRRDQueryDataSource']
// consolidation_function carries the designer's flat shape, not the wire's.
export type MetricBackendItem = Omit<
  components['schemas']['CustomGraphMetricBackendDataSource'],
  'consolidation_function'
> & { consolidation_function: DesignerConsolidationFunction }
export type ConstantItem = components['schemas']['CustomGraphConstantDataSource']
export type ScalarItem = components['schemas']['CustomGraphScalarDataSource']
/**
 * The API schema with `ast` swapped for the parser's `Formula` — same shape, but with
 * non-empty function operands and the `ArithmeticNode` subset. Assignable to the API
 * type (writes pass through, see `toApiAst`); reads narrow via `fromApiAst`.
 */
export type FormulaItem = Omit<components['schemas']['CustomGraphRRDFormulaDataSource'], 'ast'> & {
  ast: Formula
}

export type GraphItem =
  | RRDMetricItem
  | RRDQueryItem
  | MetricBackendItem
  | ConstantItem
  | ScalarItem
  | FormulaItem

/** The `type` discriminant of every item kind (API spelling: `rrd_metric`, `rrd_formula`, …). */
export type ItemType = GraphItem['type']

/** How a line is drawn (API spelling: `stack`, not the former `stacked`). */
export type LineType = RRDMetricItem['line_type']

export const LINE_TYPES: readonly LineType[] = ['line', 'area', 'stack']

/** Narrows a dropdown value to a line type. */
export function parseLineType(value: string | null): LineType | undefined {
  return LINE_TYPES.find((candidate) => candidate === value)
}

/** The tab a type belongs to. Drives list filtering and the "cannot mix" rule. */
export type Domain = 'rrd' | 'metric_backend'

/** The single source for which item kinds produce N lines instead of one. */
const MULTI_LINE_TYPES = ['rrd_query', 'metric_backend'] as const
type MultiLineType = (typeof MULTI_LINE_TYPES)[number]

/** Items that produce exactly one line and therefore carry a `color`. */
export type SingleLineItem = Exclude<GraphItem, { type: MultiLineType }>

export type FormulaDraft = { type: 'rrd_formula'; ast: Formula; title: string; color: string }

export function domainOf(type: ItemType): Domain {
  return type === 'metric_backend' ? 'metric_backend' : 'rrd'
}

/** Dynamic items (RRD queries) yield N series and must be consolidated before use in a formula. */
export function isDynamic(type: ItemType): boolean {
  return type === 'rrd_query'
}

/** Narrows to formula items. */
export function isFormula<T extends { type: ItemType }>(
  item: T
): item is Extract<T, { type: 'rrd_formula' }> {
  return item.type === 'rrd_formula'
}

/** Narrows to items that produce exactly one line. */
export function isSingleLine<T extends { type: ItemType }>(
  item: T
): item is Exclude<T, { type: MultiLineType }> {
  return !MULTI_LINE_TYPES.some((type) => type === item.type)
}

/** A data source as the REST API types it. */
export type ApiDataSource = components['schemas']['CustomGraphDefinition']['data_sources'][number]

/** A data source as API responses type it (formula asts arrive with loosened operand arrays). */
export type ApiDataSourceInput =
  | Exclude<ApiDataSource, { type: 'rrd_formula' }>
  | (Omit<components['schemas']['CustomGraphRRDFormulaDataSource'], 'ast'> & {
      ast: ApiFormulaNodeInput
    })
