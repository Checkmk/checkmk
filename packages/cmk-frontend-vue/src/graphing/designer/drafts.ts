/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { collectDirectRefs, fromApiAst, toApiAst } from './calculation/formula'
import { consolidationFromWire, consolidationToWire } from './consolidation'
import {
  type ApiDataSource,
  type ApiDataSourceInput,
  type ConstantItem,
  DEFAULT_TITLE_MACRO,
  type FormulaItem,
  type GraphItem,
  type ItemId,
  type MetricBackendItem,
  type RRDMetricItem,
  type RRDQueryItem,
  type ScalarItem,
  isFormula
} from './types'

/** The API shape with the given not-yet-configured fields widened to `| null`. */
type WithNullable<T, K extends keyof T> = Omit<T, K> & { [P in K]: T[P] | null }

export type DraftRRDMetricItem = WithNullable<
  RRDMetricItem,
  'host_name' | 'service_name' | 'metric_name'
>
export type DraftRRDQueryItem = WithNullable<RRDQueryItem, 'metric_name'>
export type DraftMetricBackendItem = WithNullable<MetricBackendItem, 'metric_name'>
export type DraftConstantItem = WithNullable<ConstantItem, 'value'>
export type DraftScalarItem = WithNullable<ScalarItem, 'host_name' | 'service_name' | 'metric_name'>

/** What the designer table holds; every `GraphItem` is assignable to it. */
export type DesignerItem =
  | DraftRRDMetricItem
  | DraftRRDQueryItem
  | DraftMetricBackendItem
  | DraftConstantItem
  | DraftScalarItem
  | FormulaItem

/** Converts a wire-format data source to a designer item; throws on an invalid formula ast. */
export function fromApiDataSource(source: ApiDataSourceInput): GraphItem {
  switch (source.type) {
    case 'rrd_formula':
      return { ...source, ast: fromApiAst(source.ast) }
    case 'metric_backend':
      return {
        ...source,
        consolidation_function: consolidationFromWire(source.consolidation_function)
      }
    default:
      return source
  }
}

function toApiDataSource(item: GraphItem): ApiDataSource {
  if (isFormula(item)) {
    return { ...item, ast: toApiAst(item.ast) }
  }
  if (item.type === 'metric_backend') {
    return { ...item, consolidation_function: consolidationToWire(item.consolidation_function) }
  }
  return item
}

/**
 * The given rows in wire form, in table order, minus the formulas whose refs (transitively)
 * reach a row the caller left out — the backend rejects dangling refs.
 */
export function toApiDataSources(items: readonly GraphItem[]): ApiDataSource[] {
  const kept = new Map(items.map((item) => [item.id, item]))
  let pruned = true
  while (pruned) {
    pruned = false
    for (const item of kept.values()) {
      if (isFormula(item) && collectDirectRefs(item.ast).some((ref) => !kept.has(ref))) {
        kept.delete(item.id)
        pruned = true
      }
    }
  }
  return items.flatMap((item) => {
    const keptItem = kept.get(item.id)
    if (keptItem === undefined) {
      return []
    }
    return [toApiDataSource(keptItem)]
  })
}

export function newRrdMetricDraft(id: ItemId, color: string): DraftRRDMetricItem {
  return {
    id,
    type: 'rrd_metric',
    title: DEFAULT_TITLE_MACRO,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color,
    host_name: null,
    service_name: null,
    metric_name: null,
    consolidation: 'max'
  }
}

export function newRrdQueryDraft(id: ItemId): DraftRRDQueryItem {
  return {
    id,
    type: 'rrd_query',
    title: DEFAULT_TITLE_MACRO,
    line_type: 'line',
    mirrored: false,
    visible: true,
    context: {},
    metric_name: null,
    consolidation: 'max'
  }
}

export function newMetricBackendDraft(id: ItemId): DraftMetricBackendItem {
  return {
    id,
    type: 'metric_backend',
    title: DEFAULT_TITLE_MACRO,
    line_type: 'line',
    mirrored: false,
    visible: true,
    metric_name: null,
    attribute_filter: { type: 'and', conjuncts: [] },
    consolidation_function: { type: 'gauge_last', lookback_seconds: 300 }
  }
}

function appearanceOf(
  item: DraftRRDMetricItem | DraftRRDQueryItem
): Pick<DraftRRDMetricItem, 'title' | 'line_type' | 'mirrored' | 'visible'> {
  return {
    title: item.title,
    line_type: item.line_type,
    mirrored: item.mirrored,
    visible: item.visible
  }
}

export function rrdMetricToQueryDraft(item: DraftRRDMetricItem): DraftRRDQueryItem {
  return { ...newRrdQueryDraft(item.id), ...appearanceOf(item) }
}

export function rrdQueryToMetricDraft(item: DraftRRDQueryItem, color: string): DraftRRDMetricItem {
  return { ...newRrdMetricDraft(item.id, color), ...appearanceOf(item) }
}

export function newConstantDraft(id: ItemId, color: string): DraftConstantItem {
  return {
    id,
    type: 'constant',
    title: DEFAULT_TITLE_MACRO,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color,
    value: null
  }
}

export function newScalarDraft(id: ItemId, color: string): DraftScalarItem {
  return {
    id,
    type: 'scalar',
    title: DEFAULT_TITLE_MACRO,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color,
    host_name: null,
    service_name: null,
    metric_name: null,
    scalar_type: 'warning'
  }
}

/** Warning/critical scalars use the fixed threshold colors; the others keep the fallback. */
export function scalarColor(
  scalarType: ScalarItem['scalar_type'],
  fallback: string,
  thresholds: { warning: string; critical: string }
): string {
  switch (scalarType) {
    case 'warning':
    case 'warning_lower':
      return thresholds.warning
    case 'critical':
    case 'critical_lower':
      return thresholds.critical
    case 'min':
    case 'max':
      return fallback
  }
}
