/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DesignerItem } from './drafts'
import type { GraphItem, ItemId } from './types'

/** An API field a source must carry before it can be saved. */
type RequiredField = 'host_name' | 'service_name' | 'metric_name' | 'value'

type FieldIssue =
  | { field: 'title' | RequiredField; code: 'required' }
  | { field: 'value' | 'consolidation_function'; code: 'not-finite' }
  | {
      field: 'consolidation_function'
      code: 'lookback-too-small' | 'percentile-out-of-range' | 'thresholds-unordered'
    }

export type RowIssue = { id: ItemId } & FieldIssue

export type RowField = RowIssue['field']

function isFilled(value: string | null): boolean {
  return value !== null && value.trim() !== ''
}

function isEntered(value: number | null): boolean {
  return value !== null && !Number.isNaN(value)
}

function requiredFieldStates(item: DesignerItem): [RequiredField, boolean][] {
  switch (item.type) {
    case 'rrd_metric':
    case 'scalar':
      return [
        ['host_name', isFilled(item.host_name)],
        ['service_name', isFilled(item.service_name)],
        ['metric_name', isFilled(item.metric_name)]
      ]
    case 'rrd_query':
    case 'metric_backend':
      return [['metric_name', isFilled(item.metric_name)]]
    case 'constant':
      return [['value', isEntered(item.value)]]
    case 'rrd_formula':
      return []
  }
}

/** The required fields this source has yet to fill in, in form order. */
function missingRequiredFields(item: DesignerItem): RequiredField[] {
  return requiredFieldStates(item).flatMap(([field, entered]) => (entered ? [] : [field]))
}

function consolidationIssues(
  id: ItemId,
  consolidation: Extract<DesignerItem, { type: 'metric_backend' }>['consolidation_function']
): RowIssue[] {
  const issues: RowIssue[] = []
  // Negated comparisons so a NaN, which loses every comparison, still counts as out of range.
  if (!(consolidation.lookback_seconds >= 1)) {
    issues.push({ id, field: 'consolidation_function', code: 'lookback-too-small' })
  }
  if (
    consolidation.type === 'histogram_quantile' &&
    !(consolidation.percentile >= 0 && consolidation.percentile <= 100)
  ) {
    issues.push({ id, field: 'consolidation_function', code: 'percentile-out-of-range' })
  }
  if (
    consolidation.type === 'histogram_fraction_below' &&
    !Number.isFinite(consolidation.threshold)
  ) {
    issues.push({ id, field: 'consolidation_function', code: 'not-finite' })
  }
  if (
    consolidation.type === 'histogram_fraction_between' &&
    !(consolidation.lower_threshold < consolidation.upper_threshold)
  ) {
    issues.push({ id, field: 'consolidation_function', code: 'thresholds-unordered' })
  }
  return issues
}

/** What blocks this source on its own, ignoring how it relates to the others. */
export function validateRow(item: DesignerItem): RowIssue[] {
  const issues: RowIssue[] = []
  if (item.title.trim() === '') {
    issues.push({ id: item.id, field: 'title', code: 'required' })
  }
  for (const field of missingRequiredFields(item)) {
    issues.push({ id: item.id, field, code: 'required' })
  }
  if (
    item.type === 'constant' &&
    (item.value === Number.POSITIVE_INFINITY || item.value === Number.NEGATIVE_INFINITY)
  ) {
    issues.push({ id: item.id, field: 'value', code: 'not-finite' })
  }
  if (item.type === 'metric_backend') {
    issues.push(...consolidationIssues(item.id, item.consolidation_function))
  }
  return issues
}

/** Narrows a source the rules accept to the shape the API takes. */
export function isValid(item: DesignerItem): item is GraphItem {
  return validateRow(item).length === 0
}
