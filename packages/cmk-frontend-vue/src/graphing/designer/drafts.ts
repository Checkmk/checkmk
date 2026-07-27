/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { collectDirectRefs, fromApiAst, toApiAst } from './calculation/formula'
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

/** Narrows a designer row to the API-complete shape. */
export function isComplete(item: DesignerItem): item is GraphItem {
  switch (item.type) {
    case 'rrd_metric':
    case 'scalar':
      return item.host_name !== null && item.service_name !== null && item.metric_name !== null
    case 'constant':
      return item.value !== null
    case 'rrd_query':
    case 'metric_backend':
      return item.metric_name !== null
    case 'rrd_formula':
      return true
  }
}

/** Converts a wire-format data source to a designer item; throws on an invalid formula ast. */
export function fromApiDataSource(source: ApiDataSourceInput): GraphItem {
  return source.type === 'rrd_formula' ? { ...source, ast: fromApiAst(source.ast) } : source
}

/**
 * The rows in wire form, in table order. Incomplete rows are dropped, as are formulas whose
 * refs (transitively) reach a dropped row — the backend rejects dangling refs.
 */
export function toApiDataSources(items: readonly DesignerItem[]): ApiDataSource[] {
  const kept = new Map(items.filter(isComplete).map((item) => [item.id, item]))
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
    const completeItem = kept.get(item.id)
    if (completeItem === undefined) {
      return []
    }
    return [
      isFormula(completeItem) ? { ...completeItem, ast: toApiAst(completeItem.ast) } : completeItem
    ]
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

/** Switches a single-metric draft to a dynamic query, keeping the metric and consolidation. */
export function rrdMetricToQueryDraft(item: DraftRRDMetricItem): DraftRRDQueryItem {
  return {
    id: item.id,
    type: 'rrd_query',
    title: item.title,
    line_type: item.line_type,
    mirrored: item.mirrored,
    visible: item.visible,
    context: {},
    metric_name: item.metric_name,
    consolidation: item.consolidation
  }
}

/** Switches a dynamic query back to a single metric; the query filters cannot be mapped over. */
export function rrdQueryToMetricDraft(item: DraftRRDQueryItem, color: string): DraftRRDMetricItem {
  return {
    id: item.id,
    type: 'rrd_metric',
    title: item.title,
    line_type: item.line_type,
    mirrored: item.mirrored,
    visible: item.visible,
    color,
    host_name: null,
    service_name: null,
    metric_name: item.metric_name,
    consolidation: item.consolidation
  }
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
